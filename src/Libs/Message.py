from __future__ import annotations

from typing import Union, Optional, List, TYPE_CHECKING
from telegram import CallbackQuery, Message as PTBMessage
from telegram.constants import ChatType, ChatMemberStatus
from Helpers.JsonObject import JsonObject

if TYPE_CHECKING:
    from telegram import Chat, User
    from Libs import SuperClient


class Message:
    _media_types = [
        "voice",
        "animation",
        "audio",
        "photo",
        "video",
        "document",
        "video_note",
        "sticker",
    ]

    def __init__(
        self,
        client: SuperClient,
        message_or_callback: Union[PTBMessage, CallbackQuery],
    ) -> None:
        self._client: SuperClient = client
        self.is_callback: bool = isinstance(message_or_callback, CallbackQuery)
        self._m: PTBMessage = message_or_callback.message if self.is_callback else message_or_callback  # type: ignore

        self.chat: Chat = self._m.chat
        self.chat_id: int = self.chat.id
        self.chat_type: str = self.chat.type
        self.chat_title: Optional[str] = (
            self.chat.title if self.chat.type != ChatType.PRIVATE else None
        )

        self.sender_raw: User = (
            message_or_callback.from_user
            if self.is_callback
            else self._m.from_user
        )
        self.reply_to_message: Optional[PTBMessage] = self._m.reply_to_message

        self.query_id: Optional[str] = (
            message_or_callback.id if self.is_callback else None
        )
        self.message_id: int = self._m.message_id
        self.message: str = (
            message_or_callback.data
            if self.is_callback
            else (self._m.caption or self._m.text or "")
        )

        self.sender: Optional[JsonObject] = None
        self.reply_to_user: Optional[JsonObject] = None

        self.msg_type: Optional[str] = None
        self.file_id: Optional[str] = None

        self.is_self: bool = False
        self.bot_username: Optional[str] = None
        self.bot_userid: Optional[int] = None
        self.bot_is_admin: bool = False
        self.user_status: Optional[str] = None
        self.is_admin: bool = False

        self.urls: List[str] = []
        self.numbers: List[int] = []
        self.mentioned: List[JsonObject] = []
        self.user_roles: dict[int, str] = {}

    async def _get_profile_id(self, user_id: int) -> Optional[str]:
        try:
            photos = await self._client.bot.get_user_profile_photos(
                user_id, limit=1
            )
            return (
                photos.photos[0][-1].file_id if photos.total_count > 0 else None
            )
        except Exception as e:
            self._client.log.warning(
                f"[WARN][_get_profile_id] Failed for {user_id}: {e}"
            )
            return None

    async def _get_user_permissions(
        self, user_id: int
    ) -> Optional[dict[str, bool]]:
        if self.chat_type == ChatType.PRIVATE:
            return None
        try:
            member = await self._client.get_chat_member(self.chat_id, user_id)
            if member.status == ChatMemberStatus.ADMINISTRATOR:
                return {
                    "can_change_info": member.can_change_info,
                    "can_delete_messages": member.can_delete_messages,
                    "can_invite_users": member.can_invite_users,
                    "can_pin_messages": member.can_pin_messages,
                    "can_promote_members": member.can_promote_members,
                    "can_restrict_members": member.can_restrict_members,
                }
        except Exception as e:
            self._client.log.warning(
                f"[WARN][_get_user_permissions] for {user_id}: {e}"
            )
        return None

    async def _get_user_role(self, user_id: int) -> str:
        if self.chat_type == ChatType.PRIVATE:
            return "user"
        try:
            member = await self._client.get_chat_member(self.chat_id, user_id)
            if member.status == ChatMemberStatus.OWNER:
                return "owner"
            elif member.status == ChatMemberStatus.ADMINISTRATOR:
                return "admin"
        except Exception as e:
            self._client.log.warning(
                f"[WARN][_get_user_role] Could not fetch role for {user_id}: {e}"
            )
        return "member"

    async def _get_mentioned_users(self, text: str) -> List[JsonObject]:
        mentioned = []
        for word in text.split():
            if not word.startswith("@"):
                continue
            try:
                user: User = await self._client.get_users(word)
                full_name = (
                    f"{user.first_name or ''} {user.last_name or ''}".strip()
                )
                profile_id = await self._get_profile_id(user.id)
                role = await self._get_user_role(user.id)
                perms = await self._get_user_permissions(user.id)

                self.user_roles[user.id] = role

                mentioned.append(
                    JsonObject(
                        {
                            "user_id": user.id,
                            "user_name": user.username,
                            "user_full_name": full_name,
                            "user_profile_id": profile_id,
                            "user_role": role,
                            "permissions": perms,
                        }
                    )
                )
            except Exception as e:
                self._client.log.error(
                    f"[ERROR][_get_mentioned_users] Could not resolve {word}: {e}"
                )
        return mentioned

    def _extract_media(self) -> None:
        # Priority 1: replied message
        if self.reply_to_message:
            for mtype in self._media_types:
                media = getattr(self.reply_to_message, mtype, None)
                if media:
                    self.msg_type = mtype
                    self.file_id = (
                        media[-1].file_id
                        if isinstance(media, list)
                        else getattr(media, "file_id", None)
                    )
                    return

        # Priority 2: original message
        for mtype in self._media_types:
            media = getattr(self._m, mtype, None)
            if media:
                self.msg_type = mtype
                self.file_id = (
                    media[-1].file_id
                    if isinstance(media, list)
                    else getattr(media, "file_id", None)
                )
                return

    async def build(self) -> Message:
        me = await self._client.get_me()
        self.bot_userid = me.id
        self.bot_username = me.username
        self.is_self = self.sender_raw.id == me.id

        self._extract_media()

        self.urls = self._client.utils.get_urls(self.message)
        self.numbers = self._client.utils.extract_numbers(self.message)

        # Sender
        sender_role = await self._get_user_role(self.sender_raw.id)
        sender_profile_id = await self._get_profile_id(self.sender_raw.id)
        sender_perms = await self._get_user_permissions(self.sender_raw.id)
        self.user_roles[self.sender_raw.id] = sender_role
        self.sender = JsonObject(
            {
                "user_id": self.sender_raw.id,
                "user_name": self.sender_raw.username,
                "user_full_name": self.sender_raw.full_name,
                "user_profile_id": sender_profile_id,
                "user_role": sender_role,
                "permissions": sender_perms,
            }
        )

        # Reply-to user
        if self.reply_to_message and self.reply_to_message.from_user:
            reply_user = self.reply_to_message.from_user
            if reply_user.id != self.sender_raw.id:
                role = await self._get_user_role(reply_user.id)
                profile_id = await self._get_profile_id(reply_user.id)
                perms = await self._get_user_permissions(reply_user.id)
                self.user_roles[reply_user.id] = role
                self.reply_to_user = JsonObject(
                    {
                        "user_id": reply_user.id,
                        "user_name": reply_user.username,
                        "user_full_name": reply_user.full_name,
                        "user_profile_id": profile_id,
                        "user_role": role,
                        "permissions": perms,
                    }
                )

        # Bot is admin?
        if self.chat_type != ChatType.PRIVATE:
            bot_member = await self._client.get_chat_member(
                self.chat_id, self.bot_userid
            )
            self.bot_is_admin = bot_member.status in {
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
            }

        self.is_admin = sender_role in {"admin", "owner"}

        # Mentioned users
        self.mentioned = await self._get_mentioned_users(self.message)
        if self.reply_to_user:
            self.mentioned.append(self.reply_to_user)

        return self
