"""Expected-path deviations and transparent automation ranking."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from .domain import Event
from .mining import (
    automation_score,
    case_metrics,
    variant_stats,
)


def conformance(path: Iterable[str], expected: list[str]) -> dict[str, Any]:
    actual = list(path)
    positions = [expected.index(x) for x in actual if x in expected]
    return {
        "missing": [x for x in expected if x not in actual],
        "unexpected": [x for x in actual if x not in expected],
        "rework": sorted(x for x, n in Counter(actual).items() if n > 1),
        "out_of_order": positions != sorted(positions),
    }


def conformance_report(
    events: Iterable[Event], expected: list[str]
) -> list[dict[str, Any]]:
    return conformance_report_from_cases(case_metrics(events), expected)


def conformance_report_from_cases(
    cases: Iterable[dict[str, Any]], expected: list[str]
) -> list[dict[str, Any]]:
    return [
        dict(case_id=x["case_id"], **conformance(x["path"], expected))
        for x in cases
    ]


def automation_candidates(
    events: Iterable[Event], expected: list[str]
) -> list[dict[str, Any]]:
    return automation_candidates_from_stats(
        variant_stats(events), case_metrics(events), expected
    )


def automation_candidates_from_stats(
    variants: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    expected: list[str],
) -> list[dict[str, Any]]:
    total = sum(v["frequency"] for v in variants) or 1
    conf = conformance_report_from_cases(cases, expected)
    rate = (
        sum(bool(x["missing"] or x["unexpected"] or x["out_of_order"]) for x in conf)
        / len(conf)
        if conf
        else 0
    )
    return [
        {
            "path": v["path"],
            "score": automation_score(
                v["frequency"] / total,
                min(1, v["cycle_p95_seconds"] / max(1, v["cycle_p50_seconds"]) - 1),
                max(0, 1 - (len(v["path"]) - 2) / 10),
                rate,
            ),
            "exception_rate": round(rate, 4),
        }
        for v in variants
    ]
