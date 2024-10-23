import asyncio
import contextlib

import uvloop

from poptimizer import config
from poptimizer.adapters import http, lgr, mongo
from poptimizer.handlers import view
from poptimizer.service.bus import bus, msg


async def _run() -> None:
    cfg = config.Cfg()

    async with contextlib.AsyncExitStack() as stack:
        http_client = await stack.enter_async_context(http.client())
        mongo_client = await stack.enter_async_context(mongo.client(cfg.mongo_db_uri))

        tg = await stack.enter_async_context(asyncio.TaskGroup())
        lgr.init(
            tg,
            http_client,
            cfg.telegram_token,
            cfg.telegram_chat_id,
        )
        repo = mongo.Repo(mongo_client[cfg.mongo_db_db])
        viewer = view.Viewer(repo)
        bus.run(
            msg.Bus(tg, repo),
            http_client,
            mongo_client[cfg.mongo_db_db],
            viewer,
        )


def run() -> None:
    """Запускает асинхронное приложение, которое может быть остановлено SIGINT.

    Настройки передаются через .env файл.
    """
    uvloop.run(_run())