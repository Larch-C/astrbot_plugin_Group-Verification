from astrbot.api.event import Event, Filter, Listener
from astrbot.api.star import Star

class QQGroupVerifyPlugin(Star):
    __starname__ = "astrbot_plugin_group_verification"
    __version__ = "1.0.2"

    def __init__(self):
        self.config = self.get_config()

    async def handle_event(self, event: Event):
        # 支持指定群号白名单，空则全群生效
        allowed_groups = self.config.get("group_whitelist", [])
        if allowed_groups and event.group_id not in allowed_groups:
            return

        member_name = event.member_name or str(event.user_id)
        verification_keyword = self.config.get("verification_keyword", "进行验证")
        verification_timeout = self.config.get("verification_timeout", 300)
        kick_delay = self.config.get("kick_delay", 60)

        join_prompt = self.config.get(
            "join_prompt",
            '欢迎 {member_name} 加入本群！请在{timeout}分钟内@机器人并回复"{verification_keyword}"完成验证，否则将被踢出群聊。'
        )

        prompt = join_prompt.format(
            member_name=member_name,
            timeout=verification_timeout // 60,
            verification_keyword=verification_keyword,
        )

        await event.reply(prompt)

    @Listener(Filter.notice_group_increase)
    async def on_group_increase(self, event: Event):
        await self.handle_event(event)
