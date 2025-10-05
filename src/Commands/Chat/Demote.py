from __future__ import annotations
from Libs import BaseCommand
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import User
    from Libs import SuperClient, Message
    from Handler import CommandHandler


class Command(BaseCommand):
    def __init__(self, client: SuperClient, handler: CommandHandler) -> None:
        super().__init__(
            client,
            handler,
            {
                "command": "demote",
                "category": "chat",
                "description": {
                    "content": "Demote one or more admins to regular users.",
                    "usage": "<@mention> or <reply>",
                },
                "chat": True,
                "admin": True,
                "admin_permissions": ["can_promote_members"],
                "xp": 3,
            },
        )

    async def exec(self, M: Message, context: list[Any]) -> None:
        try:
            users: list[User] = []

            if M.reply_to_user:
                users.append(M.reply_to_user)
            elif M.mentioned:
                users.extend(M.mentioned)

            if not users:
                await self.client.send_message(
                    chat_id=M.chat_id,
                    text="❗ Please mention at least one user or reply to their message to demote them.",
                    reply_to_message_id=M.message_id,
                )
                return

            for user in users:

                # 🔒 Prevent self-demotion
                if user.user_id == M.sender.user_id:
                    await self.client.send_message(
                        chat_id=M.chat_id,
                        text="❌ You can't demote yourself.",
                        reply_to_message_id=M.message_id,
                    )
                    continue

                # 🔒 Prevent demoting the group owner
                member = await self.client.bot.get_chat_member(
                    M.chat_id, user.user_id
                )
                if member.status == "creator":
                    await self.client.send_message(
                        chat_id=M.chat_id,
                        text=f"❌ Cannot demote group owner: {user.user_full_name}",
                        reply_to_message_id=M.message_id,
                    )
                    continue

                # 🔒 Prevent bot-demotion
                if user.user_id == M.bot_user_id:
                    await self.client.send_message(
                        chat_id=M.chat_id,
                        text="❌ I can't demote myself.",
                        reply_to_message_id=M.message_id,
                    )
                    continue

                # ✅ Demote
                await self.client.bot.promote_chat_member(
                    chat_id=M.chat_id,
                    user_id=user.user_id,
                    can_change_info=False,
                    can_post_messages=False,
                    can_edit_messages=False,
                    can_delete_messages=False,
                    can_invite_users=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_promote_members=False,
                    is_anonymous=False,
                )

                await self.client.send_message(
                    chat_id=M.chat_id,
                    text=f"✅ Demoted @{user.user_name or user.user_full_name} to regular user.",
                    reply_to_message_id=M.message_id,
                )

        except Exception as e:
            await self.client.send_message(
                chat_id=M.chat_id,
                text="❌ Failed to demote user(s).",
                reply_to_message_id=M.message_id,
            )
            self.client.log.error(f"[ERROR] [Demote] {e}")
