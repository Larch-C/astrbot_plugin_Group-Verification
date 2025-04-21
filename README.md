# 🤖 QQ群成员验证插件

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-AstrBot-purple.svg)

*一个简单高效的QQ群验证工具，保护您的群聊免受广告机器人和恶意用户的侵扰*

[功能简介](#✨-功能简介) •
[安装方法](#📥-安装方法) •
[配置说明](#⚙️-配置说明) •
[使用教程](#📝-使用教程) •
[常见问题](#❓-常见问题) •
[更新日志](#📋-更新日志)

</div>

---

## ✨ 功能简介

QQ群成员验证插件为AstrBot提供了强大的新成员管理功能，能有效过滤可疑用户，提升群聊质量。

- 🔍 **自动监测** - 实时检测新成员入群并立即发送验证提示
- 🔑 **关键词验证** - 用户需要@机器人并回复指定关键词完成验证
- ⏱️ **超时踢出** - 未在规定时间内完成验证的用户将被自动移出群聊
- 🎨 **高度自定义** - 所有提示消息和时间设置均可根据需求调整
- 🔄 **变量支持** - 提示信息支持动态变量，使消息更加个性化

## 📥 安装方法

<details>
<summary>展开查看详细安装步骤</summary>

1. 进入AstrBot的插件管理界面
2. 搜索"astrbot_plugin_Group Verification"或直接上传插件文件
3. 点击安装按钮完成插件安装
4. 在插件配置页面进行相关设置
5. 重启机器人使配置生效或者手动下载源代码自行复制到astrbot插件目录中

</details>

## ⚙️ 配置说明

### 基础配置

| 配置项 | 说明 | 默认值 |
|:-------|:-----|:-------|
| `verification_word` | 验证关键词 | `验证` |
| `verification_timeout` | 验证超时时间(秒) | `300` |
| `kick_countdown` | 踢出倒计时(秒) | `60` |

### 消息模板配置

| 配置项 | 说明 | 默认值 |
|:-------|:-----|:-------|
| `welcome_message` | 验证成功提示语 | `恭喜你验证成功，欢迎加入群聊！` |
| `failure_message` | 验证失败提示语 | `验证失败，你将在{countdown}秒后被踢出该群聊` |
| `kick_message` | 踢出提示语 | `{member_name}未完成验证，已被踢出群聊` |
| `join_prompt` | 入群提示语 | `欢迎 {member_name} 加入本群！请在{timeout}分钟内@机器人并回复"{verification_word}"完成验证，否则将被踢出群聊。` |

### 支持的模板变量

- `{member_name}` - 用户昵称或QQ号
- `{timeout}` - 验证超时分钟数
- `{countdown}` - 踢出倒计时秒数
- `{verification_word}` - 配置的验证关键词

## 📝 使用教程

<table>
  <tr>
    <td width="50%">
      <h3>1️⃣ 确保权限</h3>
      <p>请确保机器人拥有管理员权限，特别是"踢出成员"权限。</p>
    </td>
    <td width="50%">
      <h3>2️⃣ 验证流程</h3>
      <p>新用户入群后，机器人自动发送验证提示。用户需要在规定时间内@机器人并回复验证关键词。</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>3️⃣ 验证成功</h3>
      <p>验证成功的用户将收到欢迎消息，可以正常参与群聊活动。</p>
    </td>
    <td width="50%">
      <h3>4️⃣ 验证失败</h3>
      <p>超时未验证的用户会收到警告，之后将被自动踢出群聊。</p>
    </td>
  </tr>
</table>

## ❓ 常见问题

<details>
<summary><b>机器人没有响应新成员入群？</b></summary>
<p>请检查机器人是否有群事件接收权限，或者设置管理员，以及AstrBot的QQ平台连接是否正常。</p>
</details>

<details>
<summary><b>验证成功但用户仍被踢出？</b></summary>
<p>可能是验证消息格式问题。请确保用户同时满足：1) @机器人 2) 消息中包含验证关键词。</p>
</details>

<details>
<summary><b>如何设置多个验证关键词？</b></summary>
<p>当前版本仅支持单一关键词，未来版本将考虑添加多关键词支持。</p>
</details>

## 📋 更新日志

### v1.0.1 (2025-04-21)
- 🐛 修复验证关键词匹配逻辑
- ✨ 增加用户ID类型兼容处理
- 📝 完善日志记录

### v1.0.0 (2025-04-20)
- 🚀 插件首次发布
- ✅ 基础验证功能实现
- 🔧 可配置验证关键词和超时时间

## 💻 开发者信息

<img src="https://avatars.githubusercontent.com/u/huotuo146?v=4" width="100" height="100" align="right" style="border-radius:50%"/>

### huotuo146

- 🌐 [GitHub](https://github.com/huntuo146)
- 📧 Email: [2996603469@qq.com]
- 🔗 项目地址: [astrbot_plugin_Group-Verification](https://github.com/huntuo146/astrbot_plugin_Group-Verification)

## 📜 许可证

本项目采用 [MIT 许可证](LICENSE) 进行开源。

---

<div align="center">
<p>如果您觉得这个插件有用，请考虑给项目一个⭐Star！</p>
<p>有问题或建议? 欢迎 <a href="https://github.com/huntuo146/astrbot_plugin_Group-Verification/issues/new">提交Issue</a></p>

<sub>Made with ❤️ by huotuo146</sub>
</div>
