import asyncio
from collections.abc import Iterator
from types import TracebackType
from typing import Protocol, Self

from poptimizer import errors
from poptimizer.adapters import adapter, mongo
from poptimizer.domain import domain
from poptimizer.domain.evolve import organism
from poptimizer.use_cases import handler


class _IdentityMap:
    def __init__(self) -> None:
        self._seen: dict[tuple[type, domain.UID], tuple[domain.Entity, bool]] = {}
        self._lock = asyncio.Lock()

    def __iter__(self) -> Iterator[domain.Entity]:
        yield from (model for model, for_update in self._seen.values() if for_update)

    async def __aenter__(self) -> Self:
        await self._lock.acquire()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._lock.release()

    def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID,
        *,
        for_update: bool,
    ) -> E | None:
        entity, update_flag = self._seen.get((t_entity, uid), (None, False))
        if entity is None:
            return None

        if not isinstance(entity, t_entity):
            raise errors.ControllersError(f"type mismatch in identity map for {t_entity}({uid})")

        self._seen[entity.__class__, entity.uid] = (entity, update_flag or for_update)

        return entity

    def save(self, entity: domain.Entity, *, for_update: bool) -> None:
        saved, _ = self._seen.get((entity.__class__, entity.uid), (None, False))
        if saved is not None:
            raise errors.ControllersError(f"{entity.__class__}({entity.uid}) in identity map ")

        self._seen[entity.__class__, entity.uid] = (entity, for_update)

    def delete(self, entity: domain.Entity) -> None:
        if self._seen.pop((entity.__class__, entity.uid), None) is None:
            raise errors.ControllersError(f"no {entity.__class__}({entity.uid}) in identity map ")


class Bus(Protocol):
    def publish(self, msg: handler.Msg) -> None: ...


class UOW:
    def __init__(self, repo: mongo.Repo) -> None:
        self._repo = repo
        self._identity_map = _IdentityMap()

    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(adapter.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=False):
                return loaded

            repo_entity = await self._repo.get(t_entity, uid)

            identity_map.save(repo_entity, for_update=False)

            return repo_entity

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E:
        uid = uid or domain.UID(adapter.get_component_name(t_entity))
        async with self._identity_map as identity_map:
            if loaded := identity_map.get(t_entity, uid, for_update=True):
                return loaded

            repo_entity = await self._repo.get(t_entity, uid)

            identity_map.save(repo_entity, for_update=True)

            return repo_entity

    async def delete(self, entity: domain.Entity) -> None:
        async with self._identity_map as identity_map:
            identity_map.delete(entity)
            await self._repo.delete(entity)

    async def count_orgs(self) -> int:
        return await self._repo.count_orgs()

    async def next_org(self) -> organism.Organism:
        async with self._identity_map as identity_map:
            repo_entity = await self._repo.next_org()

            if loaded := identity_map.get(organism.Organism, repo_entity.uid, for_update=True):
                return loaded

            identity_map.save(repo_entity, for_update=True)

            return repo_entity

    async def sample_orgs(self, n: int) -> list[organism.Organism]:
        return await self._repo.sample_orgs(n)

    async def delete_all[E: domain.Entity](self, t_entity: type[E]) -> None:
        await self._repo.delete_all(t_entity)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_value is not None:
            return

        async with asyncio.TaskGroup() as tg:
            for entity in self._identity_map:
                tg.create_task(self._repo.save(entity))
