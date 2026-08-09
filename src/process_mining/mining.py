"""Trace discovery and metric calculations."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from statistics import median
from typing import Any

from .domain import Event
from .normalization import correlate


def percentile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    return values[round((len(values) - 1) * fraction)] if values else 0.0


def case_metrics(events: Iterable[Event]) -> list[dict[str, Any]]:
    result = []
    for case_id, trace in correlate(events).items():
        path = tuple(e.action for e in trace)
        result.append(
            {
                "case_id": case_id,
                "path": path,
                "cycle_seconds": max(
                    0, (trace[-1].timestamp - trace[0].timestamp).total_seconds()
                )
                if len(trace) > 1
                else 0.0,
                "rework": sum(n - 1 for n in Counter(path).values() if n > 1),
                "event_ids": [e.event_id for e in trace],
            }
        )
    return result


def variant_stats(events: Iterable[Event]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in case_metrics(events):
        groups[item["path"]].append(item)
    total = sum(map(len, groups.values())) or 1
    return sorted(
        (
            {
                "path": path,
                "frequency": len(cases),
                "share": round(len(cases) / total, 6),
                "cycle_p50_seconds": median([c["cycle_seconds"] for c in cases]),
                "cycle_p95_seconds": percentile(
                    [c["cycle_seconds"] for c in cases], 0.95
                ),
                "rework_count": sum(c["rework"] for c in cases),
            }
            for path, cases in groups.items()
        ),
        key=lambda x: (-x["frequency"], x["path"]),
    )


def edges(events: Iterable[Event]) -> list[dict[str, Any]]:
    waits: dict[tuple[str, str], list[float]] = defaultdict(list)
    for trace in correlate(events).values():
        for left, right in zip(trace, trace[1:]):
            waits[(left.action, right.action)].append(
                max(0, (right.timestamp - left.timestamp).total_seconds())
            )
    return sorted(
        (
            {
                "from": left,
                "to": right,
                "frequency": len(values),
                "cycle_p50_seconds": median(values),
                "cycle_p95_seconds": percentile(values, 0.95),
            }
            for (left, right), values in waits.items()
        ),
        key=lambda x: (-x["frequency"], x["from"], x["to"]),
    )


def bottlenecks(events: Iterable[Event]) -> list[dict[str, Any]]:
    return sorted(
        edges(events), key=lambda x: (-x["cycle_p95_seconds"], -x["frequency"])
    )


def automation_score(
    frequency: float, variance: float, manual_steps: float, exception_rate: float
) -> float:
    return round(
        max(
            0,
            min(
                1,
                0.35 * frequency
                + 0.25 * (1 - variance)
                + 0.25 * manual_steps
                + 0.15 * (1 - exception_rate),
            ),
        ),
        4,
    )
