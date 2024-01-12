import asyncio
from typing import Final

import pandas as pd
from pydantic import BaseModel, NonNegativeFloat, PositiveFloat, PositiveInt

from poptimizer.core import domain
from poptimizer.data import quotes, securities

_MINIMUM_HISTORY: Final = 84 * 5 + 21


class Security(BaseModel):
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat


class SecData(domain.Response):
    securities: dict[str, Security]


class GetSecData(domain.Request[SecData]):
    day: domain.Day


class SecDataRequestHandler:
    async def handle(self, ctx: domain.Ctx, request: GetSecData) -> SecData:
        sec_table = await ctx.get(securities.Securities, for_update=False)

        tickers = [sec.ticker for sec in sec_table.df]
        quotes = await _quotes(ctx, tickers)
        turnover = (  # type: ignore[reportUnknownMemberType]
            _turnover(tickers, quotes, request.day)  # type: ignore[reportUnknownMemberType]
            .iloc[-_MINIMUM_HISTORY:]
            .sort_index(ascending=True)
            .expanding()
            .median()
            .min()
        )

        return SecData(
            securities={
                sec.ticker: Security(
                    lot=sec.lot,
                    price=quotes[n].iloc[-1]["close"],  # type: ignore[reportUnknownMemberType]
                    turnover=turnover[sec.ticker],  # type: ignore[reportUnknownMemberType]
                )
                for n, sec in enumerate(sec_table.df)
            }
        )


def _turnover(
    tickers: list[str],
    quotes: list[pd.DataFrame],
    day: domain.Day,
) -> pd.DataFrame:
    turnover = pd.concat(  # type: ignore[reportUnknownMemberType]
        [quote["turnover"] for quote in quotes],
        axis=1,
        sort=True,
    )
    turnover.columns = tickers

    return turnover.fillna(0).loc[:day]  # type: ignore[reportUnknownMemberType]


async def _quotes(ctx: domain.Ctx, tickers: list[str]) -> list[pd.DataFrame]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_quote(ctx, ticker)) for ticker in tickers]

    return [task.result() for task in tasks]


async def _quote(ctx: domain.Ctx, ticker: str) -> pd.DataFrame:
    table = await ctx.get(quotes.Quotes, domain.UID(ticker), for_update=False)

    return pd.DataFrame(table.model_dump()["df"]).set_index("day")  # type: ignore[reportUnknownMemberType]