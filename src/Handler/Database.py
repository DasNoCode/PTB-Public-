from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Any, Dict, List

from pymodm import connect
from pymodm.errors import DoesNotExist

from Models import User, Chat, Command
from Helpers import JsonObject


class Database:
    def __init__(self, url: str):
        connect(url)

    @staticmethod
    def now() -> datetime:
        return datetime.now(ZoneInfo("Asia/Kolkata"))

    def _update_or_create_user(self, user_id: int, updates: dict) -> None:
        try:
            user = User.objects.raw({"user_id": str(user_id)}).first()
            for key, value in updates.items():
                setattr(user, key, value)
            user.save()
        except DoesNotExist:
            updates["user_id"] = user_id
            updates["created_at"] = self.now()
            User(**updates).save()

    def _update_or_create_group(self, chat_id: int, updates: dict) -> None:
        try:
            chat = Chat.objects.raw({"user_id": str(chat_id)}).first()
            for key, value in updates.items():
                setattr(chat, key, value)
            chat.save()
        except DoesNotExist:
            updates["user_id"] = chat_id
            Chat(**updates).save()

    def update_user_ban(self, user_id: int, ban: bool, reason: str) -> None:
        self._update_or_create_user(
            user_id, {"ban": ban, "reason": reason, "banned_at": self.now()}
        )

    def add_xp(self, user_id: int, xp: int) -> None:
        try:
            user = User.objects.raw({"user_id": str(user_id)}).first()
            user.xp += xp
            user.save()
        except DoesNotExist:
            self._update_or_create_user(user_id, {"xp": xp})

    def set_group_events(self, chat_id: int, events_status: bool) -> None:
        self._update_or_create_group(chat_id, {"events": events_status})

    def set_group_mod(self, chat_id: int, mod_status: bool) -> None:
        self._update_or_create_group(chat_id, {"mod": mod_status})

    def get_user_by_user_id(self, user_id: int) -> Any:
        try:
            return User.objects.raw({"user_id": str(user_id)}).first()
        except DoesNotExist:
            self._update_or_create_user(user_id, {})
            return JsonObject({"user_id": str(user_id), "xp": 0, "ban": False})

    def get_group_by_chat_id(self, chat_id: int) -> Any:
        try:
            return Chat.objects.raw({"user_id": str(chat_id)}).first()
        except DoesNotExist:
            self._update_or_create_group(chat_id, {})
            return JsonObject(
                {"user_id": str(chat_id), "mod": False, "events": False}
            )

    def enable_command(self, config: Any, reason: str, enable: bool) -> None:
        try:
            command = Command.objects.raw({"name": config.name}).first()
            command.aliases = getattr(config, "aliases", [])
            command.reason = reason
            command.enable = enable
            command.created_at = self.now()
            command.save()
        except DoesNotExist:
            Command(
                name=config.name,
                aliases=getattr(config, "aliases", []),
                reason=reason,
                enable=enable,
                created_at=self.now(),
            ).save()

    def get_cmd_info(self, name: str) -> Any:
        try:
            return Command.objects.raw({"name": name}).first()
        except DoesNotExist:
            Command(name=name).save()
            return JsonObject(
                {"name": name, "aliases": [], "reason": "", "enable": True}
            )

    def get_all_users_data(
        self, field: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = User.objects.all()
        results: List[Dict[str, Any]] = []

        for user in query:
            if field:
                user_dict = {
                    "user_id": getattr(user, "user_id", None),
                    field: getattr(user, field, 0),
                }
            else:
                user_dict = user.to_son().to_dict()
            results.append(user_dict)

        return results
