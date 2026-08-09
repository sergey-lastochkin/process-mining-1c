"""Compatibility facade and deterministic synthetic generator."""

from __future__ import annotations

import random
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from .conformance import automation_candidates, conformance, conformance_report
from .domain import Event
from .exports import dot, graph_json, mermaid
from .mining import (
    automation_score,
    bottlenecks,
    case_metrics,
    edges,
    percentile,
    variant_stats,
)
from .normalization import correlate, normalise, normalize, pseudo, traces


def generate(n_cases: int = 2_000, seed: int = 7) -> list[Event]:
    rnd = random.Random(seed)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    result = []
    sequence = 0
    variants = [
        (["Order", "Reserve", "Sale", "Invoice", "Payment", "Close"], 0.68),
        (
            [
                "Order",
                "Reserve",
                "Fix",
                "Reserve",
                "Sale",
                "Invoice",
                "Payment",
                "Close",
            ],
            0.17,
        ),
        (["Order", "Sale", "Invoice", "Payment", "Close"], 0.15),
    ]
    for case in range(n_cases):
        selected = variants[-1][0]
        point = rnd.random()
        total = 0.0
        for path, weight in variants:
            total += weight
            if point <= total:
                selected = path
                break
        timestamp = base + timedelta(minutes=case)
        for action in selected:
            sequence += 1
            timestamp += timedelta(seconds=rnd.randint(2, 60))
            result.append(
                Event(
                    f"e{sequence}",
                    f"case-{case}",
                    timestamp,
                    f"user{case % 20}",
                    action,
                    object_ref=f"DOC-{case}",
                    duration_ms=rnd.randint(10, 500),
                )
            )
    return result


def export_report(
    events: Iterable[Event], expected: list[str] | None = None
) -> dict[str, Any]:
    frozen = list(events)
    expected = expected or ["Order", "Reserve", "Sale", "Invoice", "Payment", "Close"]
    return {
        "events": len(frozen),
        "cases": len(correlate(frozen)),
        "variants": variant_stats(frozen),
        "bottlenecks": bottlenecks(frozen),
        "conformance": conformance_report(frozen, expected),
        "automation": automation_candidates(frozen, expected),
        "graph": graph_json(frozen),
    }


__all__ = [
    "Event",
    "automation_candidates",
    "automation_score",
    "bottlenecks",
    "case_metrics",
    "conformance",
    "conformance_report",
    "correlate",
    "dot",
    "edges",
    "export_report",
    "generate",
    "graph_json",
    "mermaid",
    "normalise",
    "normalize",
    "percentile",
    "pseudo",
    "traces",
    "variant_stats",
]
