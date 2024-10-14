import asyncio
import random
from datetime import timedelta
from typing import Final

from poptimizer.domain.entity.dl import datasets, risk
from poptimizer.domain.entity.dl.wave_net import backbone, head, inputs, wave_net
from poptimizer.domain.service import view
from poptimizer.domain.service.dl import builder, trainer
from poptimizer.service.common import logging
from poptimizer.service.fsm import states

_NEW_FORECAST_PROBABILITY: Final = 0.1
_STEP_DURATION: Final = timedelta(hours=1)
_TICKERS: Final = (
    "ABIO",
    "ABRD",
    "AFKS",
    "AFLT",
    "AKMB",
    "AKME",
    "AKRN",
    "ALRS",
    "AMEZ",
    "APTK",
    "AQUA",
    "BANE",
    "BANEP",
    "BELU",
    "BRZL",
    "BSPB",
    "CBOM",
    "CHMF",
    "CHMK",
    "CNTL",
    "CNTLP",
    "DIVD",
    "DVEC",
    "ELFV",
    "ENPG",
    "EQMX",
    "ETLN",
    "FEES",
    "FESH",
    "FLOT",
    "GAZP",
    "GCHE",
    "GEMA",
    "GEMC",
    "GMKN",
    "GOLD",
    "HYDR",
    "IRAO",
    "IRKT",
    "KAZT",
    "KAZTP",
    "KLSB",
    "KMAZ",
    "KRKNP",
    "KZOS",
    "KZOSP",
    "LKOH",
    "LNZL",
    "LNZLP",
    "LQDT",
    "LSNG",
    "LSNGP",
    "LSRG",
    "MAGN",
    "MDMG",
    "MGNT",
    "MGTSP",
    "MOEX",
    "MRKC",
    "MRKP",
    "MRKS",
    "MRKU",
    "MRKV",
    "MRKY",
    "MRKZ",
    "MSNG",
    "MSRS",
    "MSTT",
    "MTLR",
    "MTLRP",
    "MTSS",
    "MVID",
    "NFAZ",
    "NKHP",
    "NKNC",
    "NKNCP",
    "NLMK",
    "NMTP",
    "NVTK",
    "OBLG",
    "OGKB",
    "OZON",
    "PHOR",
    "PIKK",
    "PLZL",
    "PMSB",
    "PMSBP",
    "PRFN",
    "RASP",
    "RGSS",
    "RNFT",
    "ROLO",
    "ROSN",
    "RTKM",
    "RTKMP",
    "RUAL",
    "SBER",
    "SBERP",
    "SBGB",
    "SBMM",
    "SBMX",
    "SBRB",
    "SELG",
    "SFIN",
    "SGZH",
    "SIBN",
    "SMLT",
    "SNGS",
    "SNGSP",
    "SPBE",
    "SVAV",
    "TATN",
    "TATNP",
    "TBRU",
    "TCSG",
    "TGKA",
    "TGKB",
    "TGKN",
    "TMOS",
    "TRMK",
    "TRNFP",
    "TRUR",
    "TTLK",
    "UNAC",
    "UNKL",
    "UPRO",
    "VKCO",
    "VRSB",
    "VSMO",
    "VTBR",
    "YAKG",
)
_OPTIMIZATION_DURATION: Final = timedelta(minutes=1)
_DESC: Final = trainer.DLModel(
    batch=trainer.Batch(
        size=320,
        feats=builder.Features(
            close=True,
            div=True,
            ret=True,
        ),
        days=datasets.Days(
            history=252,
            forecast=21,
            test=64,
        ),
    ),
    net=wave_net.Cfg(
        input=inputs.Cfg(use_bn=True, out_channels=32),
        backbone=backbone.Cfg(blocks=1, kernels=32, channels=32, out_channels=32),
        head=head.Cfg(channels=32, mixture_size=4),
    ),
    optimizer=trainer.Optimizer(),
    scheduler=trainer.Scheduler(epochs=3, max_lr=0.0015),
    utility=risk.Cfg(risk_tolerance=0.5),
)


class EvolutionAction:
    def __init__(self, lgr: logging.Service, view_service: view.Service) -> None:
        self._lgr = lgr
        self._view_service = view_service

    async def __call__(self) -> states.States:
        await asyncio.sleep(_STEP_DURATION.total_seconds())

        last_day = await self._view_service.last_day()
        bldr = builder.Builder(self._view_service)
        tr = trainer.Trainer(self._lgr, bldr)
        await tr.test_model(_TICKERS, last_day, _DESC, None)

        match random.random() < _NEW_FORECAST_PROBABILITY:  # noqa: S311
            case True:
                return states.States.OPTIMIZATION
            case False:
                return states.States.DATA_UPDATE
