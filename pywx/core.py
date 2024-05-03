import os
import json
import typing

import psutil
import pyee
import traceback
import socketserver

import requests

from .events import ALL_MESSAGE, SYSTEM_MESSAGE
from .logger import logger
from .utils import WeChatManager, start_wechat_with_inject, fake_wechat_version, parse_event


class RequestHandler(socketserver.BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self):
        try:
            data = b""
            while True:
                chunk = self.request.recv(1024)
                data += chunk
                if len(chunk) == 0 or chunk[-1] == 0xA:
                    break

            wechat = getattr(self.server, "wechat")
            wechat.on_event(data)
            self.request.sendall("200 OK".encode())
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            self.request.close()


class Bot:

    def __init__(self, faked_version: typing.Union[str, None] = None):
        self.version = "3.9.5.81"
        self.server_host = "127.0.0.1"
        self.remote_host = "127.0.0.1"
        self.faked_version = faked_version
        self.event_emitter = pyee.EventEmitter()
        self.wechat_manager = WeChatManager()
        self.remote_port, self.server_port = self.wechat_manager.get_port()
        self.BASE_URL = f"http://{self.remote_host}:{self.remote_port}"
        self.webhook_url = None
        self.info = None
        self.DATA_SAVE_PATH = None
        self.FILE_SAVE_PATH = None
        self.IMAGE_SAVE_PATH = None
        self.VIDEO_SAVE_PATH = None

        code, output = start_wechat_with_inject(self.remote_port)
        if code == 1:
            raise Exception(output)

        self.process = psutil.Process(int(output))

        if self.faked_version is not None:
            if fake_wechat_version(self.process.pid, self.version, faked_version) == 0:
                logger.info(f"wechat version faked: {self.version} -> {faked_version}")
            else:
                logger.info(f"wechat version fake failed.")

        self.wechat_manager.add(self.process.pid, self.remote_port, self.server_port)
        self.handle(SYSTEM_MESSAGE, once=True)(self.init_bot)
        self.hook_sync_msg(self.server_host, self.server_port)

    def init_bot(self, bot: "Bot", event: dict):
        message = parse_event(event)
        if message["content"]["sysmsg"]["@type"] == "SafeModuleCfg":
            bot.info = bot.get_self_info()["data"]
            self.DATA_SAVE_PATH = bot.info["dataSavePath"]
            self.FILE_SAVE_PATH = os.path.join(self.DATA_SAVE_PATH, "wxhelper/file")
            self.IMAGE_SAVE_PATH = os.path.join(self.DATA_SAVE_PATH, "wxhelper/image")
            self.VIDEO_SAVE_PATH = os.path.join(self.DATA_SAVE_PATH, "wxhelper/video")
            logger.info(f"Bot(pid={self.process.pid}, name=\"{self.info['name']}\")")

    def set_webhook_url(self, webhook_url: str):
        self.webhook_url = webhook_url

    def webhook(self, event: dict):
        if self.webhook_url is not None:
            try:
                requests.post(self.webhook_url, json=event)
            except Exception:
                pass

    def call_api(self, api: str, *args, **kwargs):
        return requests.request("POST", self.BASE_URL + api, *args, **kwargs).json()

    def hook_sync_msg(
            self,
            ip: str,
            port: int,
            enable_http: int = 0,
            url: str = "http://127.0.0.1:8000",
            timeout: int = 30
    ):
        """hook同步消息"""
        data = {
            "port": port,
            "ip": ip,
            "enableHttp": enable_http,
            "url": url,
            "timeout": timeout
        }
        return self.call_api("/api/hookSyncMsg", json=data)

    def unhook_sync_msg(self):
        """取消hook同步消息"""
        return self.call_api("/api/unhookSyncMsg")

    def hook_log(self):
        """hook日志"""
        return self.call_api("/api/hookLog")

    def unhook_log(self):
        """取消hook日志"""
        return self.call_api("/api/unhookLog")

    def check_login(self):
        """检查登录状态"""
        return self.call_api("/api/checkLogin")

    def get_self_info(self):
        """获取用户信息"""
        return self.call_api("/api/userInfo")

    def send_text(self, wxid: str, msg: str):
        """发送文本消息"""
        data = {
            "wxid": wxid,
            "msg": msg
        }
        return self.call_api("/api/sendTextMsg", json=data)

    def send_image(self, wxid: str, image_path: str):
        """发送图片消息"""
        data = {
            "wxid": wxid,
            "imagePath": image_path
        }
        return self.call_api("/api/sendImagesMsg", json=data)

    def send_emotion(self, wxid: str, file_path: str):
        """发送表情消息"""
        data = {
            "wxid": wxid,
            "filePath": file_path
        }
        return self.call_api("/api/sendCustomEmotion", json=data)

    def send_file(self, wxid: str, file_path: str):
        """发送文件消息"""
        data = {
            "wxid": wxid,
            "filePath": file_path
        }
        return self.call_api("/api/sendFileMsg", json=data)

    def send_applet(
        self,
        wxid: str,
        waid_contact: str,
        waid: str,
        applet_wxid: str,
        json_param: str,
        head_img_url: str,
        main_img: str,
        index_page: str
    ):
        """发送小程序消息"""
        data = {
            "wxid": wxid,
            "waidConcat": waid_contact,
            "waid": waid,
            "appletWxid": applet_wxid,
            "jsonParam": json_param,
            "headImgUrl": head_img_url,
            "mainImg": main_img,
            "indexPage": index_page
        }
        return self.call_api("/api/sendApplet", json=data)

    def send_room_at(self, room_id: str, wxids: list[str], msg: str):
        """发送群@消息"""
        data = {
            "chatRoomId": room_id,
            "wxids": ",".join(wxids),
            "msg": msg
        }
        return self.call_api("/api/sendAtText", json=data)

    def send_pat(self, room_id: str, wxid: str):
        """发送拍一拍消息"""
        data = {
            "receiver": room_id,
            "wxid": wxid
        }
        return self.call_api("/api/sendPatMsg", json=data)

    def get_contacts(self):
        """获取联系人列表"""
        return self.call_api("/api/getContactList")

    def get_contact(self, wxid: str):
        """获取联系人详情"""
        data = {
            "wxid": wxid
        }
        return self.call_api("/api/getContactProfile", json=data)

    def create_room(self, member_ids: list[str]):
        """创建群聊"""
        data = {
            "memberIds": ",".join(member_ids)
        }
        return self.call_api("/api/createChatRoom", json=data)

    def quit_room(self, room_id: str):
        """退出群聊"""
        data = {
            "chatRoomId": room_id
        }
        return self.call_api("/api/quitChatRoom", json=data)

    def get_room(self, room_id: str):
        """获取群详情"""
        data = {
            "chatRoomId": room_id
        }
        return self.call_api("/api/getChatRoomDetailInfo", json=data)

    def get_room_members(self, room_id: str):
        """获取群成员列表"""
        data = {
            "chatRoomId": room_id
        }
        return self.call_api("/api/getMemberFromChatRoom", json=data)

    def add_room_member(self, room_id: str, member_ids: list[str]):
        """添加群成员"""
        data = {
            "chatRoomId": room_id,
            "memberIds": ",".join(member_ids)
        }
        return self.call_api("/api/addMemberToChatRoom", json=data)

    def delete_room_member(self, room_id: str, member_ids: list[str]):
        """删除群成员"""
        data = {
            "chatRoomId": room_id,
            "memberIds": ",".join(member_ids)
        }
        return self.call_api("/api/delMemberFromChatRoom", json=data)

    def invite_room_member(self, room_id: str, member_ids: list[str]):
        """邀请群成员"""
        data = {
            "chatRoomId": room_id,
            "memberIds": ",".join(member_ids)
        }
        return self.call_api("/api/InviteMemberToChatRoom", json=data)

    def modify_member_nickname(self, room_id: str, wxid: str, nickname: str):
        """修改群成员昵称"""
        data = {
            "chatRoomId": room_id,
            "wxid": wxid,
            "nickName": nickname
        }
        return self.call_api("/api/modifyNickname", json=data)

    def top_msg(self, msg_id: int):
        """设置群置顶消息"""
        data = {
            "msgId": msg_id
        }
        return self.call_api("/api/topMsg", json=data)

    def remove_top_msg(self, room_id: str, msg_id: int):
        """移除群置顶消息"""
        data = {
            "chatRoomId": room_id,
            "msgId": msg_id
        }
        return self.call_api("/api/removeTopMsg", json=data)

    def forward_msg(self, msg_id: int, wxid: str):
        """转发消息"""
        data = {
            "msgId": msg_id,
            "wxid": wxid
        }
        return self.call_api("/api/forwardMsg", json=data)

    def get_sns_first_page(self):
        """获取朋友圈首页"""
        return self.call_api("/api/getSNSFirstPage")

    def get_sns_next_page(self, sns_id: int):
        """获取朋友圈下一页"""
        data = {
            "snsId": sns_id
        }
        return self.call_api("/api/getSNSNextPage", json=data)

    def collect_msg(self, msg_id: int):
        """收藏消息"""
        data = {
            "msgId": msg_id
        }
        return self.call_api("/api/addFavFromMsg", json=data)

    def collect_image(self, wxid: str, image_path: str):
        """收藏图片"""
        data = {
            "wxid": wxid,
            "imagePath": image_path
        }
        return self.call_api("/api/addFavFromImage", json=data)

    def download_attachment(self, msg_id: int):
        """下载附件"""
        data = {
            "msgId": msg_id
        }
        return self.call_api("/api/downloadAttach", json=data)

    def forward_public_msg(
        self,
        wxid: str,
        app_name: str,
        username: str,
        title: str,
        url: str,
        thumb_url: str,
        digest: str
    ):
        """转发公众号消息"""
        data = {
            "wxid": wxid,
            "appName": app_name,
            "userName": username,
            "title": title,
            "url": url,
            "thumbUrl": thumb_url,
            "digest": digest,
        }
        return self.call_api("/api/forwardPublicMsg", json=data)

    def forward_public_msg_by_msg_id(self, wxid: str, msg_id: int):
        """转发公众号消息通过消息ID"""
        data = {
            "wxid": wxid,
            "msg_id": msg_id
        }
        return self.call_api("/api/forwardPublicMsgByMsgId", json=data)

    def decode_image(self, file_path: str, store_dir: str):
        """解码图片"""
        data = {
            "filePath": file_path,
            "storeDir": store_dir
        }
        return self.call_api("/api/decodeImage", json=data)

    def get_voice_by_msg_id(self, msg_id: int, store_dir: str):
        """获取语音通过消息ID"""
        data = {
            "msgId": msg_id,
            "storeDir": store_dir
        }
        return self.call_api("/api/getVoiceByMsgId", json=data)

    def ocr(self, image_path: str):
        """图片文本识别"""
        data = {
            "imagePath": image_path
        }
        return self.call_api("/api/ocr", json=data)

    def get_db_info(self):
        """获取数据库句柄"""
        return self.call_api("/api/getDBInfo")

    def exec_sql(self, db_handle: int, sql: str):
        """执行SQL命令"""
        data = {
            "dbHandle": db_handle,
            "sql": sql
        }
        return self.call_api("/api/execSql", json=data)

    def test(self):
        """测试"""
        return self.call_api("/api/test")

    def on_event(self, data: str):
        try:
            event = json.loads(data)
            logger.debug(event)
            self.event_emitter.emit(str(ALL_MESSAGE), self, event)
            self.event_emitter.emit(str(event["type"]), self, event)
            self.webhook(event)
        except Exception:
            logger.error(traceback.format_exc())

    def handle(self, events: typing.Union[list[str], str, None] = None, once: bool = False):
        def wrapper(func):
            listen = self.event_emitter.on if not once else self.event_emitter.once
            if not events:
                if not once:
                    listen(str(ALL_MESSAGE), func)
                else:
                    listen(str(ALL_MESSAGE), func)
            else:
                for event in events if isinstance(events, list) else [events]:
                    listen(str(event), func)

        return wrapper

    def exit(self):
        self.process.terminate()

    def run(self):
        try:
            server = socketserver.ThreadingTCPServer((self.server_host, self.server_port), RequestHandler)
            server.wechat = self
            logger.info(f"{self.server_host}:{self.server_port}")
            server.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            self.exit()
