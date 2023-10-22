from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import MongoDsn


@asynccontextmanager
async def client(uri: MongoDsn) -> AsyncIterator[AgnosticClient]:
    motor = AsyncIOMotorClient(str(uri), tz_aware=False)
    try:
        yield motor
    finally:
        motor.close()