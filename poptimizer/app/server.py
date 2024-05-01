from aiohttp import web
from pydantic import HttpUrl

from poptimizer.adapters import backup, telegram, uow
from poptimizer.adapters.server import Server
from poptimizer.data import services
from poptimizer.ui import api, frontend, middleware


async def run(
    telegram_lgr: telegram.Logger,
    ctx_factory: uow.CtxFactory,
    url: HttpUrl,
    backup_srv: backup.Service,
) -> None:
    handlers = _prepare_handlers(telegram_lgr, ctx_factory, backup_srv)
    server = Server(
        telegram_lgr,
        handlers,
        url,
    )

    await server()


def _prepare_handlers(
    telegram_lgr: telegram.Logger,
    ctx_factory: uow.CtxFactory,
    backup_srv: backup.Service,
) -> web.Application:
    sub_app = web.Application()
    api.Handlers(sub_app, ctx_factory, services.Portfolio(), services.Dividends(backup_srv.backup))

    app = web.Application(middlewares=[middleware.RequestErrorMiddleware(telegram_lgr)])
    app.add_subapp("/api/", sub_app)
    frontend.Handlers(app)

    return app
