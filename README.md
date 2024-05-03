# npywx

## 介绍

- 基于pc微信hook的api接口

支持的接口
1. hook同步消息
2. 取消hook同步消息
3. hook日志
4. 取消hook日志
5. 检查登录状态
6. 获取用户信息
7. 发送文本消息
8. 发送图片消息
9. 发送文件消息
10. 发送表情消息
11. 发送小程序消息
12. 发送群@消息
13. 发送拍一拍消息
14. 获取联系人列表
15. 获取联系人详情
16. 创建群聊
17. 退出群聊
18. 获取群详情
19. 获取群成员列表
20. 添加群成员
21. 删除群成员
22. 邀请群成员
23. 修改群成员昵称
24. 设置群置顶消息
25. 移除群置顶消息
26. 转发消息
27. 获取朋友圈首页
28. 获取朋友圈下一页
29. 收藏消息
30. 收藏图片
31. 下载附件
32. 转发公众号消息
33. 转发公众号消息通过消息ID
34. 解码图片
35. 获取语音通过消息ID
36. 图片文本识别
37. 获取数据库句柄
38. 执行SQL命令
39. 测试
  
## 支持的微信版本下载
- [WeChatSetup3.9.5.81.exe](https://github.com/tom-snow/wechat-windows-versions/releases/download/v3.9.5.81/WeChatSetup-3.9.5.81.exe)

## 安装

```bash
pip install npywx
```

## 使用示例

```python
# import os
# os.environ["PYWX_LOG_LEVEL"] = "INFO" # 修改日志输出级别
from pywx import Bot
from pywx import events
from pywx.utils import parse_event

# faked_version解除微信低版本登录限制
bot = Bot(faked_version="3.9.10.19")


@bot.handle(events.TEXT_MESSAGE)
def on_text_message(bot: Bot, event):
    message = parse_event(event)
    self_id = bot.get_self_info()["data"]["wxid"]
    if message["fromUser"] != self_id:
        bot.send_text(message["fromUser"], message["content"])


bot.run()
```