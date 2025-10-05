from __future__ import annotations
import pkg_resources
from typing import (
    TYPE_CHECKING,
    Iterable,
    Union,
    Optional,
    List,
    Sequence,
)

from telegram import (
    Bot,
    Update,
    InputMedia,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from telegram._utils.defaultvalue import DEFAULT_NONE
from telegram._utils.types import ODVInput, JSONDict

from pyromod import Client as PyroClient

from Helpers import Utils, get_logger


if TYPE_CHECKING:
    from telegram import (
        ChatMember,
        Message as TgMessage,
        User as TgUser,
        ReactionType,
    )
    from pyrogram.types import User as PyroUser


class SuperClient:
    def __init__(self, config) -> None:
        from Handler import Database, CommandHandler

        self.config = config
        # PTB does not have a method to get a user ID from a username
        self.pyrogram_Client: PyroClient = PyroClient(
            name=config.app_name,
            api_id=config.app_id,
            api_hash=config.app_hash,
            bot_token=config.app_token,
        )

        self.bot_name: str = config.app_name
        self.prefix: str = config.prefix
        self.owner_id: int = config.owner_user_id
        self.owner_user_name: str = config.owner_user_name
        self.log = get_logger()
        self.utils = Utils(self.log, config)

        self._app: Application = (
            ApplicationBuilder().token(config.app_token).build()
        )
        self.bot: Bot = self._app.bot

        self._handler: CommandHandler = CommandHandler(self)
        self.db: Database = Database(config.url)

        self._register_handlers()

    def _register_handlers(self) -> None:
        self._app.add_handler(
            MessageHandler(filters.StatusUpdate.ALL, self._on_events)
        )
        self._app.add_handler(MessageHandler(None, self._on_message))
        self._app.add_handler(CallbackQueryHandler(self._on_message))

    async def _on_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        from Libs import Message

        if not update.message:
            return

        msg = await Message(self, update.message).build()
        await self._handler.handler(msg)

    async def _on_events(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if update.callback_query:
            pass  # Placeholder for future callback handling

    async def send_message(
        self, chat_id: Union[int, str], text: str, **kwargs
    ) -> TgMessage:
        return await self.bot.send_message(chat_id=chat_id, text=text, **kwargs)

    async def send_photo(
        self, chat_id: Union[int, str], photo: Union[str, bytes], **kwargs
    ) -> TgMessage:
        return await self.bot.send_photo(chat_id=chat_id, photo=photo, **kwargs)

    async def send_document(
        self, chat_id: Union[int, str], document: Union[str, bytes], **kwargs
    ) -> TgMessage:
        return await self.bot.send_document(
            chat_id=chat_id, document=document, **kwargs
        )

    async def send_media_group(
        self, chat_id: Union[int, str], media: List[InputMedia], **kwargs
    ) -> List[TgMessage]:
        return await self.bot.send_media_group(
            chat_id=chat_id, media=media, **kwargs
        )

    async def set_reaction(
        self,
        chat_id: Union[str, int],
        message_id: int,
        reaction: Optional[
            Union[Sequence[Union[ReactionType, str]], ReactionType, str]
        ] = None,
        is_big: Optional[bool] = None,
        *,
        read_timeout: ODVInput[float] = DEFAULT_NONE,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        api_kwargs: Optional[JSONDict] = None,
    ) -> bool:
        try:
            return await self.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=reaction,
                is_big=is_big,
                read_timeout=read_timeout,
                write_timeout=write_timeout,
                connect_timeout=connect_timeout,
                pool_timeout=pool_timeout,
                api_kwargs=api_kwargs,
            )
        except Exception as e:
            self.log.error(f"[ERROR] [set_reaction] {e}")
            return False

    async def get_me(self) -> TgUser:
        return await self.bot.get_me()

    async def get_chat_member(
        self,
        chat_id: Union[str, int],
        user_id: int,
        *,
        read_timeout: Optional[float] = None,
        write_timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        pool_timeout: Optional[float] = None,
        api_kwargs: Optional[dict] = None,
    ) -> ChatMember:
        return await self.bot.get_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            read_timeout=read_timeout,
            write_timeout=write_timeout,
            connect_timeout=connect_timeout,
            pool_timeout=pool_timeout,
            api_kwargs=api_kwargs,
        )

    async def download_media(
        self, file_id: int, directory: str = "Download/"
    ) -> Optional[str]:
        file = await self.bot.get_file(file_id)
        file_path: str = f"{directory}{file_id}.jpg"
        await file.download_to_drive(custom_path=file_path)
        return file_path

    async def get_users(
        self, user_name: Union[int, str, Iterable[Union[int, str]]]
    ) -> Union[PyroUser, List[PyroUser]]:
        return await self.pyrogram_Client.get_users(user_name)

    def _log_installed_packages(self) -> None:
        installed = sorted(
            [
                (dist.project_name, dist.version)
                for dist in pkg_resources.working_set
            ],
            key=lambda x: x[0].lower(),
        )
        self.log.info("📦 Installed Python Packages in Environment:")
        for name, version in installed:
            self.log.info(f"{name}=={version}")

    def _log_ascii_banner(self, text: str = "BOT STARTED") -> None:
        banner = f"""
        ╔══════════════════════════════════╗
        ║ 🚀 {text.center(26)} 🚀 ║
        ╚══════════════════════════════════╝
        """
        self.log.info(banner)

    def run_polling(self) -> None:
        self._log_installed_packages()
        self._log_ascii_banner("TELEGRAM BOT ONLINE")
        self._handler.load_commands("src/Commands")
        self.pyrogram_Client.start()
        self._app.run_polling()
