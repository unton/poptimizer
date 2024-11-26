import logging
from typing import Final, Protocol

import bson
import pandas as pd

from poptimizer.domain import domain
from poptimizer.domain.evolve import evolve, organism
from poptimizer.use_cases import handler, view
from poptimizer.use_cases.dl import builder, trainer

_PARENT_COUNT: Final = 2


def random_org_uid() -> domain.UID:
    return domain.UID(str(bson.ObjectId()))


class Ctx(Protocol):
    async def get[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def get_for_update[E: domain.Entity](
        self,
        t_entity: type[E],
        uid: domain.UID | None = None,
    ) -> E: ...

    async def delete(self, entity: domain.Entity) -> None: ...

    async def count_orgs(self) -> int: ...

    async def next_org(self) -> organism.Organism: ...

    async def sample_orgs(self, n: int) -> list[organism.Organism]: ...


class EvolutionHandler:
    def __init__(self, viewer: view.Viewer) -> None:
        self._lgr = logging.getLogger()
        self._viewer = viewer

    async def __call__(
        self,
        ctx: Ctx,
        msg: handler.DataNotChanged | handler.DataUpdated,
    ) -> handler.EvolutionStepFinished:
        evolution = await ctx.get_for_update(evolve.Evolution)
        state = evolution.start_step(msg.day)
        self._lgr.info("%s", evolution)

        match state:
            case evolve.State.INIT:
                org = await ctx.get_for_update(organism.Organism, random_org_uid())
                await self._init_day(ctx, evolution, org)
            case evolve.State.INIT_DAY:
                org = await ctx.get_for_update(organism.Organism, evolution.org_uid)
                await self._init_day(ctx, evolution, org)
            case evolve.State.EVAL_ORG:
                org = await ctx.next_org()
                await self._eval_org(ctx, evolution, org)
            case evolve.State.CREATE_ORG:
                org = await ctx.get_for_update(organism.Organism, evolution.org_uid)
                await self._create_org(ctx, evolution, org)

        return handler.EvolutionStepFinished()

    async def _init_day(self, ctx: Ctx, evolution: evolve.Evolution, org: organism.Organism) -> None:
        tickers = await self._viewer.portfolio_tickers()
        ret_deltas = await self._eval(ctx, org, evolution.day, tickers)

        evolution.init_new_day(tickers, org.uid, ret_deltas)

    async def _eval_org(self, ctx: Ctx, evolution: evolve.Evolution, org: organism.Organism) -> None:
        while org.ver == 0:
            await ctx.delete(org)
            org = await ctx.next_org()

        ret_deltas = await self._eval(ctx, org, evolution.day, evolution.tickers)
        dead, msg = evolution.eval_org_is_dead(org.uid, ret_deltas)
        self._lgr.info(msg)

        if dead:
            await ctx.delete(org)
            self._lgr.info("Organism removed")

    async def _create_org(self, ctx: Ctx, evolution: evolve.Evolution, org: organism.Organism) -> None:
        org = await self._make_child(ctx, org)

        await self._eval_org(ctx, evolution, org)

    async def _make_child(self, ctx: Ctx, org: organism.Organism) -> organism.Organism:
        parents = await ctx.sample_orgs(_PARENT_COUNT)
        if len({parent.uid for parent in parents}) != _PARENT_COUNT:
            parents = [organism.Organism(day=org.day, rev=org.rev) for _ in range(_PARENT_COUNT)]

        child = await ctx.get_for_update(organism.Organism, random_org_uid())
        child.genes = org.make_child_genes(parents[0], parents[1], 1 / org.ver)

        return child

    async def _eval(
        self,
        ctx: Ctx,
        org: organism.Organism,
        day: domain.Day,
        tickers: tuple[domain.Ticker, ...],
    ) -> list[float]:
        cfg = trainer.Cfg.model_validate(org.phenotype)
        test_days = 1 + await ctx.count_orgs()

        tr = trainer.Trainer(builder.Builder(self._viewer))
        ret_deltas = await tr.run(tickers, pd.Timestamp(day), test_days, cfg, None)

        org.update_stats(day, tickers, ret_deltas)
        self._lgr.info(f"Return delta - {org.ret_delta:.2%}")

        return ret_deltas
