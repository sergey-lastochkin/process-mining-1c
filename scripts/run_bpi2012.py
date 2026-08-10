"""Build reproducible aggregate process-mining evidence from BPI Challenge 2012."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import tracemalloc
from collections import Counter
from pathlib import Path

from process_mining.conformance import (
    automation_candidates_from_stats,
    conformance_report_from_cases,
)
from process_mining.mining import (
    bottlenecks_from_edges,
    case_metrics_from_traces,
    edges_from_traces,
    percentile,
    variant_stats_from_cases,
)
from process_mining.normalization import group_by_case, normalise
from process_mining.xes import load_xes


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def git_revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True, cwd=Path(__file__).parents[1]
    ).strip()


def serialize_path(item: dict[str, object]) -> dict[str, object]:
    return {**item, "path": list(item["path"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--fetch-manifest", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("studies/bpi-challenge-2012-2026-08-10"),
    )
    args = parser.parse_args()
    source = json.loads(args.fetch_manifest.read_text())
    started = time.perf_counter()
    tracemalloc.start()
    loaded_events, load_report = load_xes(args.dataset, "bpi2012")
    read_seconds = time.perf_counter() - started
    normalised = normalise(loaded_events, salt="bpi2012-public-study")
    grouped = group_by_case(normalised)
    cases = case_metrics_from_traces(grouped)
    variants = variant_stats_from_cases(cases)
    direct_edges = edges_from_traces(grouped)
    bottleneck_min_frequency = 100
    material_edges = [
        edge for edge in direct_edges if edge["frequency"] >= bottleneck_min_frequency
    ]
    expected_path = list(variants[0]["path"]) if variants else []
    deviations = conformance_report_from_cases(cases, expected_path)
    candidates = automation_candidates_from_stats(variants, cases, expected_path)
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    cycle_seconds = [float(item["cycle_seconds"]) for item in cases]
    deviations_by_kind = {
        "missing": sum(bool(item["missing"]) for item in deviations),
        "unexpected": sum(bool(item["unexpected"]) for item in deviations),
        "out_of_order": sum(bool(item["out_of_order"]) for item in deviations),
        "rework": sum(bool(item["rework"]) for item in deviations),
    }
    activity_counts = Counter(event.action for event in normalised)
    source_manifest = {
        **source,
        "raw_storage": "external --data-dir (not committed)",
        "local_path": None,
        "record_count": load_report.events_loaded,
        "trace_count": load_report.traces_seen,
        "parser": "process_mining.xes.load_xes",
    }
    results = {
        "study": "BPI Challenge 2012, public XES run",
        "code_commit": git_revision(),
        "python": sys.version.split()[0],
        "source_sha256": source["calculated_sha256"],
        "parameters": {
            "correlation": "XES trace concept:name",
            "activity": "event concept:name",
            "timestamp": "event time:timestamp",
            "resource_handling": "deterministic pseudonymization before analysis",
            "reference_path": "most frequent observed variant, not a business-approved normative model",
            "percentile": "empirical nearest-index after sort",
        },
        "ingestion": load_report.as_dict(),
        "summary": {
            "events": len(normalised),
            "cases": len(grouped),
            "activities": len(activity_counts),
            "variants": len(variants),
            "directly_follows_edges": len(direct_edges),
            "bottleneck_min_transition_frequency": bottleneck_min_frequency,
            "cycle_p50_seconds": percentile(cycle_seconds, 0.50),
            "cycle_p90_seconds": percentile(cycle_seconds, 0.90),
            "cycle_p95_seconds": percentile(cycle_seconds, 0.95),
            "cases_with_rework": deviations_by_kind["rework"],
            "reference_deviation_cases": sum(
                bool(item["missing"] or item["unexpected"] or item["out_of_order"])
                for item in deviations
            ),
            "duration_seconds": round(time.perf_counter() - started, 3),
            "read_seconds": round(read_seconds, 3),
            "peak_tracemalloc_bytes": peak_memory,
        },
        "reference_path": expected_path,
        "activity_frequency": activity_counts.most_common(),
        "top_variants": [serialize_path(item) for item in variants[:20]],
        "top_bottlenecks": bottlenecks_from_edges(material_edges)[:20],
        "process_map": {"nodes": sorted(activity_counts), "edges": direct_edges},
        "deviations": {"by_kind": deviations_by_kind},
        "automation_candidates": [serialize_path(item) for item in candidates[:15]],
        "limits": [
            "The BPI log is a loan-application process, not a 1C journal.",
            "The observed top variant is a statistical comparison baseline, not a verified target process.",
            "Pseudonymization protects aggregated output but is not an organizational retention policy.",
            "A 1C registration log alone lacks business intent, correction reason and full document lifecycle context.",
        ],
    }
    write_json(args.output_dir / "source-manifest.json", source_manifest)
    write_json(args.output_dir / "results.json", results)
    print(json.dumps(results["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
