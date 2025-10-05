from __future__ import annotations
from Libs import BaseCommand
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from Libs import SuperClient, Message
    from Handler import CommandHandler


class Command(BaseCommand):
    def __init__(self, client: SuperClient, handler: CommandHandler) -> None:
        super().__init__(
            client,
            handler,
            {
                "command": "hi",
                "category": "general",
                "description": {"content": "Say hello to the bot"},
                "xp": 1,
            },
        )

    async def exec(self, M: Message, context: list[Any]) -> None:
        await self.client.send_message(
            chat_id=M.chat_id,
            text=f"Hey @{M.sender.user_name or M.sender.user_full_name}, how's your day going?",
            reply_to_message_id=M.message_id,
        )
