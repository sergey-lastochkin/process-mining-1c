from datetime import UTC, datetime, timedelta
from gzip import open as gzip_open

import pytest
from fastapi.testclient import TestClient

from process_mining.api import create_app
from process_mining.conformance import (
    automation_candidates,
    automation_score,
    conformance,
)
from process_mining.domain import Event
from process_mining.exports import dot, graph_json, mermaid
from process_mining.mining import (
    bottlenecks,
    case_metrics,
    percentile,
    variant_stats,
)
from process_mining.normalization import (
    DuplicateConflict,
    correlate,
    normalise,
    pseudo,
)
from process_mining.xes import load_xes


def ev(i, c, t, a, user="alice", ref="r"):
    return Event(
        str(i),
        c,
        datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=t),
        user,
        a,
        object_ref=ref,
    )


def test_deduplication_keeps_one():
    assert len(normalise([ev(1, "c", 1, "A"), ev(1, "c", 1, "A")])) == 1


def test_duplicate_conflict_fails_closed():
    with pytest.raises(DuplicateConflict):
        normalise([ev(1, "c", 1, "A"), ev(1, "c", 2, "B")])


def test_pseudonymization():
    assert pseudo("alice") != pseudo("bob") and "alice" not in pseudo("alice")


def test_out_of_order_is_evidenced_by_order():
    assert [x.action for x in normalise([ev(2, "c", 2, "B"), ev(1, "c", 1, "A")])] == [
        "A",
        "B",
    ]


def test_explicit_case_correlation():
    assert set(correlate([ev(1, "a", 1, "A"), ev(2, "b", 1, "A")])) == {"a", "b"}


def test_case_cycle_and_rework():
    assert case_metrics([ev(1, "c", 1, "A"), ev(2, "c", 3, "A")])[0]["rework"] == 1


def test_percentiles():
    assert (
        percentile([1, 2, 3, 4, 100], 0.5) == 3
        and percentile([1, 2, 3, 4, 100], 0.95) == 100
    )


def test_variant_frequency():
    assert (
        variant_stats(
            [
                ev(1, "a", 1, "A"),
                ev(2, "a", 2, "B"),
                ev(3, "b", 1, "A"),
                ev(4, "b", 2, "B"),
            ]
        )[0]["frequency"]
        == 2
    )


def test_transition_bottleneck():
    assert (
        bottlenecks([ev(1, "c", 1, "A"), ev(2, "c", 11, "B")])[0]["cycle_p50_seconds"]
        == 10
    )


def test_conformance_missing_unexpected_rework():
    x = conformance(["A", "B", "X", "B"], ["A", "B", "C"])
    assert x["missing"] == ["C"] and x["unexpected"] == ["X"] and x["rework"] == ["B"]


def test_conformance_out_of_order():
    assert conformance(["B", "A"], ["A", "B"])["out_of_order"]


def test_automation_score_bounds():
    assert (
        automation_score(99, -1, 99, -1) == 1 and automation_score(-1, 99, -1, 99) == 0
    )


def test_candidates_are_reported():
    assert (
        automation_candidates([ev(1, "c", 1, "A"), ev(2, "c", 2, "B")], ["A", "B"])[0][
            "score"
        ]
        >= 0
    )


def test_graph_json_and_text_exports():
    events = [ev(1, "c", 1, "A"), ev(2, "c", 2, "B")]
    assert (
        graph_json(events)["edges"]
        and "flowchart LR" in mermaid(events)
        and "digraph process" in dot(events)
    )


def test_api_processes_and_unknown_process():
    client = TestClient(create_app())
    assert client.get("/processes").status_code == 200
    assert client.get("/process/nope/variants").status_code == 404


def test_api_post_events_and_variants():
    client = TestClient(create_app())
    payload = {
        "process_id": "sales",
        "events": [
            {
                "event_id": "1",
                "case_id": "c",
                "timestamp": "2026-01-01T00:00:00Z",
                "user_id": "u",
                "action": "Order",
            },
            {
                "event_id": "2",
                "case_id": "c",
                "timestamp": "2026-01-01T00:00:02Z",
                "user_id": "u",
                "action": "Close",
            },
        ],
    }
    assert client.post("/events", json=payload).json()["accepted"] == 2
    assert client.get("/process/sales/variants").json()[0]["frequency"] == 1


def test_api_case_bottleneck_candidates_and_dot():
    client = TestClient(create_app())
    client.post(
        "/events",
        json={
            "process_id": "sales",
            "events": [
                {
                    "event_id": "1",
                    "case_id": "c",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "user_id": "u",
                    "action": "Order",
                },
                {
                    "event_id": "2",
                    "case_id": "c",
                    "timestamp": "2026-01-01T00:00:02Z",
                    "user_id": "u",
                    "action": "Close",
                },
            ],
        },
    )
    assert (
        client.get("/case/c").status_code == 200
        and client.get("/process/sales/bottlenecks").status_code == 200
        and client.get("/process/sales/automation-candidates").status_code == 200
        and "digraph" in client.get("/process/sales/graph.dot").text
    )


def test_api_missing_case_is_404():
    assert TestClient(create_app()).get("/case/nope").status_code == 404


def test_xes_loader_reads_trace_contract(tmp_path):
    source = tmp_path / "tiny.xes.gz"
    with gzip_open(source, "wt") as target:
        target.write(
            "<log><trace><string key='concept:name' value='case-1'/>"
            "<event><string key='concept:name' value='Create'/>"
            "<date key='time:timestamp' value='2020-01-01T00:00:00Z'/></event>"
            "</trace></log>"
        )
    events, report = load_xes(source, "test")
    assert events[0].event_id == "test:1" and report.as_dict()["events_loaded"] == 1
