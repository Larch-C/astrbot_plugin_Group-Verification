# QQ群聊成员验证插件

一个用于 astrbot 的 QQ 群聊成员验证插件，新成员进入群聊后需要通过 @机器人 并回复指定验证词进行验证，否则将被自动踢出。

## 功能特点

- 新成员加入自动发送验证提示
- @机器人 并回复验证词即可完成验证
- 超时未验证发出警告提示
- 持续未验证自动踢出群聊
- 验证成功显示欢迎消息

## 安装步骤

1. 确保已安装 astrbot 框架
2. 将 `member_verification.py` 文件放入 astrbot 的插件目录中
3. 重启 astrbot 或通过命令加载插件

## 配置说明

你可以在 `member_verification.py` 中修改以下参数来自定义插件行为：

- `self.verification_word` - 验证词，默认为"验证"
- `self.verification_timeout` - 验证超时时间（秒），默认为300秒（5分钟）

## 使用要求

- 机器人需要拥有踢出成员的权限
- Python 3.7 或更高版本
- astrbot 框架环境

## 常见问题

**Q: 为什么无法踢出成员？**  
A: 请确保机器人在群内拥有踢人权限（管理员或群主）。

**Q: 如何修改验证词？**  
A: 在 `member_verification.py` 中找到 `self.verification_word = "验证"` 这一行，将"验证"修改为你想要的验证词。

**Q: 如何增加验证超时时间？**  
A: 在 `member_verification.py` 中找到 `self.verification_timeout = 300` 这一行，将300修改为你想要的超时时间（单位：秒）。
