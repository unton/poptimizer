from __future__ import annotations

import itertools
import statistics

from pydantic import Field, field_validator

from poptimizer.domain import domain
from poptimizer.domain.evolve import genetics, genotype


class Organism(domain.Entity):
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    genes: genetics.Genes = Field(default_factory=lambda: genotype.DLModel.model_validate({}).genes)
    model: bytes = b""
    ret_delta: float = 0

    @property
    def phenotype(self) -> genetics.Phenotype:
        return genotype.DLModel.model_validate(self.genes).phenotype

    def make_child_genes(self, parent1: Organism, parent2: Organism, scale: float) -> genetics.Genes:
        model = genotype.DLModel.model_validate(self.genes)
        model1 = genotype.DLModel.model_validate(parent1.genes)
        model2 = genotype.DLModel.model_validate(parent2.genes)

        return model.make_child(model1, model2, scale).genes

    @field_validator("tickers")
    def _tickers_must_be_sorted(cls, tickers: list[str]) -> list[str]:
        tickers_pairs = itertools.pairwise(tickers)

        if not all(ticker < next_ for ticker, next_ in tickers_pairs):
            raise ValueError("tickers not sorted")

        return tickers

    def update_stats(self, day: domain.Day, tickers: tuple[domain.Ticker, ...], ret_deltas: list[float]) -> None:
        self.day = day
        self.tickers = tickers
        self.ret_delta = statistics.mean(ret_deltas)
