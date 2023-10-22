import datetime
from collections.abc import Iterable
from typing import Any, Final, TypeVar

from motor.core import AgnosticClient
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from poptimizer.core import domain, errors

_MONGO_ID: Final = "_id"
_REV: Final = "rev"
_VER: Final = "ver"
_UID: Final = "uid"
_TIMESTAMP: Final = "timestamp"


TEntity = TypeVar("TEntity", bound=domain.Entity)


def _collection_name(t_entity: type[TEntity]) -> str:
    return t_entity.__name__.lower()


class Mongo:
    def __init__(
        self,
        mongo_client: AgnosticClient,
        subdomain: domain.Subdomain,
    ) -> None:
        self._mongo_client = mongo_client
        self._db = str(subdomain)

    async def get(self, t_entity: type[TEntity], uid: domain.UID) -> TEntity:
        collection_name = _collection_name(t_entity)

        if (doc := await self._load(collection_name, uid)) is None:
            doc = await self._create_new(collection_name, uid)

        return self._create_entity(t_entity, doc)

    async def _load(self, collection_name: str, uid: domain.UID) -> Any:
        collection = self._mongo_client[self._db][collection_name]
        try:
            return await collection.find_one({_MONGO_ID: uid})
        except PyMongoError as err:
            raise errors.AdaptersError("can't load {collection_name}.{uid}") from err

    async def _create_new(self, collection_name: str, uid: domain.UID) -> Any:
        doc = {
            _MONGO_ID: uid,
            _VER: 0,
            _TIMESTAMP: datetime.datetime(datetime.MINYEAR, 1, 1),
        }

        collection = self._mongo_client[self._db][collection_name]

        try:
            await collection.insert_one(doc)
        except PyMongoError as err:
            raise errors.AdaptersError("can't create {collection_name}.{uid}") from err

        return doc

    def _create_entity(self, t_entity: type[TEntity], doc: Any) -> TEntity:
        doc[_REV] = {
            _UID: doc.pop(_MONGO_ID),
            _VER: doc.pop(_VER),
        }

        try:
            return t_entity.model_validate(doc)
        except ValidationError as err:
            raise errors.AdaptersError("can't create entity {collection_name}.{uid}") from err

    async def save(self, entities: Iterable[domain.Entity]) -> None:
        try:
            async with (
                await self._mongo_client.start_session() as session,
                session.start_transaction(),
            ):
                db = session.client[self._db]
                for entity in entities:
                    doc = entity.model_dump()
                    doc.pop(_REV)

                    collection_name = _collection_name(entity.__class__)
                    if (
                        await db[collection_name].find_one_and_update(
                            {_MONGO_ID: entity.uid, _VER: entity.ver},
                            {"$inc": {_VER: 1}, "$set": doc},
                            projection={_MONGO_ID: False},
                            session=session,
                        )
                        is None
                    ):
                        raise errors.AdaptersError(f"wrong version {collection_name}.{entity.uid}")
        except PyMongoError as err:
            raise errors.AdaptersError("can't save entities") from err