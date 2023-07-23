import asyncio

from aiogram import Bot, Dispatcher
from typing import List, Union

from routers.ClientsBotRouters import ClientRouters
from routers.ClientsBotRouters.ClientRouters import get_routers

from aiogram.utils.token import TokenValidationError
from aiogram.utils.i18n import I18nMiddleware
from aiogram.utils.i18n import gettext as _
from aiogram.utils.i18n import SimpleI18nMiddleware

from db.DataBaseManager import create_db

import logging

logger = logging.getLogger(__name__)
db = create_db()


class BotsManager:
    _tokens: List[str] = list()
    _bots: List[Bot] = list()

    @classmethod
    def register_bots(cls, tokens: List[str]) -> Union[Exception, List[Bot]]:
        for token in tokens:
            try:
                cls._bots.append(Bot(token=token))
                cls._tokens.append(token)
            except Exception as ex:
                logger.error(f"Couldn't register bot with \"{token}\" token.\n{type(ex)}:\n {ex}")
        return cls._bots

    @classmethod
    def register_bot(cls, token: str) -> Union[bool, Exception, Bot]:
        if token in cls._tokens:
            raise Exception(_("Бот з токеном {token} вже працює").format(token=token))
        try:
            cls._bots.append(Bot(token=token))
            cls._tokens.append(token)
        except TokenValidationError:
            raise TokenValidationError(_("Couldn't register bot with {token} token").format(token=token))
        return cls._bots[-1]

    @classmethod
    async def run(cls, i18n_middleware: SimpleI18nMiddleware) -> None:
        dp = Dispatcher()
        dp.update.middleware(i18n_middleware)
        tokens = db.bots.get_tokens()
        if not tokens:
            return
        BotsManager.register_bots(tokens=tokens)
        dp.include_routers(*ClientRouters.get_routers())

        await dp.start_polling(*cls._bots)

    @classmethod
    def add_and_run(cls, bot: Bot, lan_mw: I18nMiddleware):
        new_dp = Dispatcher()
        new_dp.update.middleware(lan_mw)
        new_dp.include_routers(*get_routers())
        asyncio.create_task(new_dp.start_polling(bot))
