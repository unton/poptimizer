from datetime import date, datetime
from enum import StrEnum, auto, unique
from typing import Annotated, Any, NewType, Protocol

import pandas as pd
from pydantic import BaseModel, ConfigDict, PlainSerializer

UID = NewType("UID", str)
Version = NewType("Version", int)


def get_component_name(component: Any) -> str:
    if isinstance(component, type):
        return component.__name__

    return component.__class__.__name__


class Revision(BaseModel):
    uid: UID
    ver: Version

    model_config = ConfigDict(frozen=True)


Day = Annotated[
    date,
    PlainSerializer(
        lambda date: datetime(
            year=date.year,
            month=date.month,
            day=date.day,
        ),
        return_type=datetime,
    ),
]

Ticker = NewType("Ticker", str)


@unique
class Currency(StrEnum):
    RUR = auto()
    USD = auto()


class Entity(BaseModel):
    rev: Revision
    day: Day

    @property
    def uid(self) -> UID:
        return self.rev.uid

    @property
    def ver(self) -> Version:
        return self.rev.ver


class Viewer(Protocol):
    async def turnover(
        self,
        last_day: Day,
        tickers: tuple[Ticker, ...],
    ) -> pd.DataFrame: ...
    async def close(
        self,
        last_day: Day,
        tickers: tuple[Ticker, ...],
    ) -> pd.DataFrame: ...


class Ctx(Protocol):
    async def get[E: Entity](
        self,
        t_entity: type[E],
        uid: UID | None = None,
        *,
        for_update: bool = True,
    ) -> E: ...
    def info(self, msg: str) -> None: ...
    def warn(self, msg: str) -> None: ...

    @property
    def viewer(self) -> Viewer: ...
