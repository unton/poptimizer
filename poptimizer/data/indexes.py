"""Загрузка биржевых индексов."""
import asyncio
import itertools
import logging
from datetime import datetime
from typing import ClassVar, Final

import aiohttp
import aiomoex
from pydantic import Field, ValidationError, validator

from poptimizer.data import domain, exceptions
from poptimizer.data.repo import Repo

_INDEXES: Final = ("MCFTRR", "MEOGTRR", "IMOEX", "RVI")


class Quote(domain.Row):
    """Котировки индекса."""

    date: datetime = Field(alias="TRADEDATE")
    close: float = Field(alias="CLOSE", gt=0)


class Table(domain.Table):
    """Таблица с котировками индекса."""

    group: ClassVar[domain.Group] = domain.Group.INDEXES
    df: list[Quote] = Field(default_factory=list)

    def last_row_date(self) -> datetime | None:
        """Дата последней строки при наличии."""
        if not self.df:
            return None

        return self.df[-1].date

    @validator("df")
    def _must_be_sorted_by_date(cls, df: list[Quote]) -> list[Quote] | None:
        dates_pairs = itertools.pairwise(row.date for row in df)

        if not all(date < next_ for date, next_ in dates_pairs):
            raise ValueError("dates are not sorted")

        return df


class IndexesSrv:
    """Сервис загрузки биржевых индексов."""

    def __init__(self, repo: Repo, session: aiohttp.ClientSession) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._repo = repo
        self._session = session

    async def update(self, update_day: datetime) -> None:
        """Обновляет котировки биржевых индексов."""
        try:
            await asyncio.gather(*[self._update_one(update_day, index) for index in _INDEXES])
        except exceptions.DataError as err:
            self._logger.warning(f"can't complete Indexes update {err}")

            return

        self._logger.info("update is completed")

    async def _update_one(self, update_day: datetime, index: str) -> None:
        table = await self._repo.get(Table, index)

        start_date = table.last_row_date()

        try:
            payload = await self._download(index, start_date, update_day)
        except (aiomoex.client.ISSMoexError, ValidationError) as err_download:
            raise exceptions.DownloadError(index) from err_download

        table = _update_table(table, payload, update_day)

        await self._repo.save(table)

    async def _download(
        self,
        index: str,
        start_date: datetime | None,
        update_day: datetime,
    ) -> domain.Payload[Quote]:
        json = await aiomoex.get_market_history(
            session=self._session,
            start=start_date and str(start_date.date()),
            end=str(update_day.date()),
            security=index,
            columns=(
                "TRADEDATE",
                "CLOSE",
            ),
            market="index",
        )

        return domain.Payload[Quote].parse_obj({"df": json})


def _update_table(table: Table, payload: domain.Payload[Quote], update_day: datetime) -> Table:
    if not table.df:
        return Table(
            _id=table.id_,
            timestamp=update_day,
            df=payload.df,
        )

    last = table.df[-1]

    if last != (first := payload.df[0]):
        raise exceptions.UpdateError(f"{table.id_} data missmatch {last} vs {first}")

    try:
        return Table(
            _id=table.id_,
            timestamp=update_day,
            df=table.df + payload.df[1:],
        )
    except ValidationError as err:
        raise exceptions.UpdateError(table.id_) from err
