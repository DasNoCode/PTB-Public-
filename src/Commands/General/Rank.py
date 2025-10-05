from __future__ import annotations
from typing import Any, TYPE_CHECKING
import os
from Libs import BaseCommand
from Helpers import get_rank

if TYPE_CHECKING:
    from telegram import User, Message
    from Libs import SuperClient
    from Handler import CommandHandler


class Command(BaseCommand):
    def __init__(self, client: SuperClient, handler: CommandHandler) -> None:
        super().__init__(
            client,
            handler,
            {
                "command": "rank",
                "category": "general",
                "description": {
                    "content": "Show the rank of a user based on XP.",
                    "usage": "<@mention> or <reply>",
                },
                "xp": 3,
            },
        )

    async def exec(self, M: Message, context: dict[str, Any]) -> None:
        try:
            users: list[User] = []

            if M.reply_to_user:
                users.append(M.reply_to_user)
            elif M.mentioned:
                users.extend(M.mentioned)
            else:
                users.append(M.sender)

            for user in users:
                db_user = self.client.db.get_user_by_user_id(user.user_id)
                xp: int = db_user.xp

                user_name = user.user_name or user.user_full_name or "User"

                rank_data: dict[str, Any] = get_rank(xp)
                level = rank_data["level"]
                rank_name = rank_data["rank_name"]
                rank_emoji = rank_data["rank_emoji"]
                next_rank_name = rank_data["next_rank_name"]
                next_rank_emoji = rank_data["next_rank_emoji"]
                next_rank_xp = rank_data["next_rank_xp"]
                current_xp = rank_data["xp"]
                level_xp_target = rank_data["level_xp_target"]
                previous_level_xp = (
                    5 * ((level - 1) ** 2) + 50 if level > 1 else 0
                )

                caption: str = context.get("flags", {}).get(
                    "caption",
                    f"🏆 Rank: {rank_name} {rank_emoji}"
                    + (
                        f"\nNext Rank: {next_rank_name} {next_rank_emoji}"
                        f"\nXP Needed: {next_rank_xp - current_xp}"
                        if next_rank_name
                        else ""
                    ),
                )

                profile_id = context.get("flags", {}).get(
                    "user_profile_id", user.user_profile_id
                )
                profile_path = await self.client.download_media(profile_id)
                avatar_url = self.client.utils.img_to_url(profile_path)
                os.remove(profile_path)

                rankcard_url = (
                    "https://vacefron.nl/api/rankcard"
                    f"?username=@{user_name}"
                    f"&avatar={avatar_url}"
                    f"&level={level}"
                    f"&rank="
                    f"&currentxp={current_xp}"
                    f"&nextlevelxp={level_xp_target}"
                    f"&previouslevelxp={previous_level_xp}"
                    f"&custombg=https://media.discordapp.net/attachments/1022533781040672839/1026849383104397312/image0.jpg"
                    f"&xpcolor=00ffff"
                    f"&isboosting=false"
                    f"&circleavatar=true"
                )

                await self.client.send_photo(
                    chat_id=M.chat_id,
                    photo=self.client.utils.fetch_buffer(rankcard_url),
                    caption=caption,
                    reply_to_message_id=M.message_id,
                )
        except Exception as e:
            await self.client.send_message(
                chat_id=M.chat_id,
                text="❌ An error occurred while getting the rank.",
                reply_to_message_id=M.message_id,
            )
            self.client.log.error(f"['ERROR'] ['Rank'] {e}")
