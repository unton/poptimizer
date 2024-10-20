import itertools
from datetime import date, datetime
from enum import StrEnum, auto, unique
from typing import Annotated, NewType, Protocol

from pydantic import BaseModel, ConfigDict, PlainSerializer

from poptimizer import consts


class POError(Exception):
    def __str__(self) -> str:
        """Выводи исходную причину ошибки при ее наличии для удобства логирования.

        https://peps.python.org/pep-3134/
        """
        errs = [repr(self)]
        cause_err: BaseException | None = self

        while cause_err := cause_err and (cause_err.__cause__ or cause_err.__context__):
            errs.append(repr(cause_err))

        return " -> ".join(errs)


class DomainError(POError): ...


UID = NewType("UID", str)
Version = NewType("Version", int)


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
AccName = NewType("AccName", str)


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


class Row(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class _RowWithDate(Protocol):
    day: Day


def sorted_by_day_validator(df: list[_RowWithDate]) -> list[_RowWithDate]:
    dates_pairs = itertools.pairwise(row.day for row in df)

    if not all(day < next_ for day, next_ in dates_pairs):
        raise ValueError("df not sorted by day")

    return df


def after_start_date_validator(df: list[_RowWithDate]) -> list[_RowWithDate]:
    if df and (day := df[0].day) < consts.START_DAY:
        raise ValueError(f"day before start day {day}")

    return df
