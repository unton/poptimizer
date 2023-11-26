import asyncio
import zoneinfo
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Final

from poptimizer.core import domain

# Часовой пояс MOEX
_MOEX_TZ: Final = zoneinfo.ZoneInfo(key="Europe/Moscow")

# Торги заканчиваются в 24.00, но данные публикуются 00.45
_END_HOUR: Final = 0
_END_MINUTE: Final = 45

_CHECK_INTERVAL: Final = timedelta(minutes=1)


class DayStartedEvent(domain.Event):
    day: domain.Day


def _last_day() -> date:
    now = datetime.now(_MOEX_TZ)
    end_of_trading = now.replace(
        hour=_END_HOUR,
        minute=_END_MINUTE,
        second=0,
        microsecond=0,
        tzinfo=_MOEX_TZ,
    )

    delta = 2
    if end_of_trading < now:
        delta = 1

    return date(
        year=now.year,
        month=now.month,
        day=now.day,
    ) - timedelta(days=delta)


class DayStartedPublisher:
    async def publish(self, bus: Callable[[domain.Event], None]) -> None:
        day = _last_day()
        bus(DayStartedEvent(day=day))

        while True:
            await asyncio.sleep(_CHECK_INTERVAL.total_seconds())
            if day < (new_day := _last_day()):
                bus(DayStartedEvent(day=(day := new_day)))
