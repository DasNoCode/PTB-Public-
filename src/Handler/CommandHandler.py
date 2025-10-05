from __future__ import annotations
from datetime import datetime
import os
import importlib.util
from typing import List, Dict, Any, TYPE_CHECKING
from Helpers import JsonObject, get_rank

if TYPE_CHECKING:
    from Libs import SuperClient, Message, BaseCommand
    from Models import Command, User


class CommandHandler:
    def __init__(self, client: SuperClient) -> None:
        self._client = client
        self._commands: Dict[str, Any] = {}

    async def handler(self, M: Message) -> None:
        context: JsonObject = JsonObject(self._parse_args(M.message))
        is_command: bool = M.message.startswith(self._client.config.prefix)
        msg_type: str = "CMD" if is_command else "MSG"
        chat_name: str = (
            M.chat_title if M.chat_type == "supergroup" else "private"
        )
        timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if is_command:
            self._client.log.info(
                f"[{msg_type}] {self._client.config.prefix}{context.cmd} from @{getattr(M.sender, 'user_name', 'user_full_name')} in {chat_name} at {timestamp}"
            )
        else:
            self._client.log.info(
                f"[{msg_type}] from {M.sender.user_name} in {chat_name} at {timestamp}"
            )
            return

        if M.message == self._client.config.prefix:
            return await self._client.send_message(
                M.chat_id,
                f"Please enter a command\u0001 starting with {self._client.config.prefix}.",
                reply_to_message_id=M.message_id,
            )

        cmd: BaseCommand | None = self._commands.get(
            context.cmd.lower()
        ) or next(
            (
                c
                for c in self._commands.values()
                if context.cmd.lower() in getattr(c.config, "aliases", [])
            ),
            None,
        )

        if not cmd:
            return await self._client.send_message(
                M.chat_id,
                f"❌ Unknown command! Use {self._client.config.prefix}help to see all available commands.",
                reply_to_message_id=M.message_id,
            )

        user: User = self._client.db.get_user_by_user_id(M.sender.user_id)
        command_info: Command = self._client.db.get_cmd_info(cmd.config.command)

        # 🚫 Ban check
        if user.ban:
            return await self._client.send_message(
                M.chat_id,
                f"🚫 Oops! You're banned from using this bot.\n"
                f"📝 Reason: {user.reason}\n"
                f"🕒 Banned at: {user.banned_at.strftime('%Y-%m-%d %H:%M:%S (%z)')}\n\n"
                f"Contact admin if this is a mistake.",
                reply_to_message_id=M.message_id,
            )

        # ⛔ Disabled command
        if not command_info.enable:
            return await self._client.send_message(
                M.chat_id,
                f"🚫 Command **{cmd.config.command}** is currently disabled.\n\n"
                f"⏰ Disabled at: {command_info.created_at.strftime('%Y-%m-%d %H:%M:%S (%z)')}\n"
                f"📝 Reason: {command_info.reason}",
            )

        # 👥 chat-only
        if getattr(cmd.config, "chat", False) and M.chat_type == "private":
            return await self._client.send_message(
                M.chat_id,
                "👥 Chat-only command. Try this in a chat.",
                reply_to_message_id=M.message_id,
            )

        # 📬 Private-only
        if getattr(cmd.config, "private", False) and M.chat_type == "chat":
            return await self._client.send_message(
                M.chat_id,
                "💬 Please use this command in private chat only.",
                reply_to_message_id=M.message_id,
            )

        # 👨‍💻 Developer-only
        if (
            getattr(cmd.config, "devOnly", False)
            and M.Info.Sender.User not in self._client.config.mods
        ):
            return await self._client.send_message(
                M.chat_id,
                "⚠️ Oops! This command is only for developers.",
                reply_to_message_id=M.message_id,
            )

        # 👮 Admin-only
        if getattr(cmd.config, "admin", False):
            if not M.is_admin:
                if not M.bot_is_admin:
                    return await self._client.send_message(
                        M.chat_id,
                        "🤖 Bot must be an admin to execute this command.",
                        reply_to_message_id=M.message_id,
                    )
                return await self._client.send_message(
                    M.chat_id,
                    "❌ You must be an admin to use this command.",
                    reply_to_message_id=M.message_id,
                )

            # ✅ Check specific admin permissions
            if M.sender.user_role == "admin":
                required_perms: list[str] = getattr(
                    cmd.config, "admin_permissions", []
                )
                for perm in required_perms:
                    if not M.sender.permissions.get(perm, False):
                        return await self._client.send_message(
                            M.chat_id,
                            f"❌ You must have '{perm}' permission to run this command.",
                            reply_to_message_id=M.message_id,
                        )

        # ✅ Execute command
        await cmd.exec(M, context)

        # 🌟 XP and rank handling
        self._client.db.add_xp(M.sender.user_id, cmd.config.xp)

        new_xp: int = user.xp + cmd.config.xp
        old_rank: dict = get_rank(user.xp)
        new_rank: dict = get_rank(new_xp)
        if old_rank["rank_name"] != new_rank["rank_name"]:
            if new_rank["next_rank_name"] is None:
                caption = (
                    f"--caption=@{getattr(M.sender, 'user_name', None) or getattr(M.sender, 'user_full_name', None)} "
                    f"You have reached the highest rank! 🏆 {new_rank['rank_name']} {new_rank['rank_emoji']}"
                    f"--user_profile_id={getattr(M.sender, 'user_profile_id', None)}"
                )
            else:
                caption = (
                    f"--caption=@{getattr(M.sender, 'user_name', None) or getattr(M.sender, 'user_full_name', None)} "
                    f"You rank up 🎉 from {old_rank['rank_name']} {old_rank['rank_emoji']} to {new_rank['rank_name']} {new_rank['rank_emoji']}"
                    f"--user_profile_id={getattr(M.sender, 'user_profile_id', None)}"
                )
            rank_cmd: BaseCommand = self._commands.get("rank")
            if rank_cmd:
                await rank_cmd.exec(M, self._parse_args(caption))

    def load_commands(self, folder_path: str) -> None:
        self._client.log.info("Loading commands...")
        all_files: List[str] = self._client.utils.readdir_recursive(folder_path)

        for file_path in all_files:
            if not file_path.endswith(".py") or os.path.basename(
                file_path
            ).startswith("_"):
                continue

            try:
                module_name = os.path.splitext(os.path.basename(file_path))[0]
                spec = importlib.util.spec_from_file_location(
                    module_name, file_path
                )

                if not spec or not spec.loader:
                    raise ImportError(f"Cannot load spec for {file_path}")

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                CommandClass = getattr(module, "Command", None)
                if not CommandClass:
                    raise AttributeError(
                        f"No class 'Command' found in {file_path}"
                    )

                instance = CommandClass(self._client, self)
                command_id: str = instance.config.command
                self._commands[command_id] = instance

                category = instance.config.get("category", "Uncategorized")
                self._client.log.info(
                    f"✅ Loaded: {command_id} from {category}"
                )

            except Exception as e:
                self._client.log.error(
                    f"[ERROR] [CommandHandler.load_commands] Failed to load {file_path}: {e}"
                )

        self._client.log.info(
            f"✅ Successfully loaded {len(self._commands)} commands."
        )

    def _parse_args(self, raw: str) -> Dict[str, Any]:
        args: List[str] = raw.split(" ")
        cmd = (
            args.pop(0).lower()[len(self._client.config.prefix) :]
            if args and args[0].startswith(self._client.config.prefix)
            else ""
        )
        text: str = " ".join(args)
        flags: Dict[str, str] = {}

        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--") and "=" in arg:
                key, value = arg[2:].split("=", 1)
                i += 1
                while (
                    i < len(args)
                    and not args[i].startswith("--")
                    and not args[i].startswith("-")
                ):
                    value += f" {args[i]}"
                    i += 1
                flags[key] = value
            elif arg.startswith("-"):
                flags[arg] = ""
                i += 1
            else:
                i += 1

        return {
            "cmd": cmd,
            "text": text,
            "flags": flags,
            "args": args,
            "raw": raw,
        }
