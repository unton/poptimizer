import aiohttp

from poptimizer.service.common import logging, uow
from poptimizer.service.fsm import evolution, fsm, optimization, states
from poptimizer.service.fsm.data import data


def prepare(
    logger: logging.Service,
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
) -> fsm.FSM[states.States]:
    graph = _prepare_graph(http_client, ctx_factory)

    return fsm.FSM(logger, graph)


def _prepare_graph(
    http_client: aiohttp.ClientSession,
    ctx_factory: uow.CtxFactory,
) -> fsm.Graph[states.States]:
    return {
        states.States.DATA_UPDATE: {
            "action": data.UpdateDataAction(http_client, ctx_factory),
            "transitions": {
                states.States.EVOLUTION_STEP,
                states.States.OPTIMIZATION,
            },
        },
        states.States.EVOLUTION_STEP: {
            "action": evolution.EvolutionAction(),
            "transitions": {
                states.States.DATA_UPDATE,
                states.States.OPTIMIZATION,
            },
        },
        states.States.OPTIMIZATION: {
            "action": optimization.OptimizationAction(),
            "transitions": {
                states.States.EVOLUTION_STEP,
            },
        },
    }