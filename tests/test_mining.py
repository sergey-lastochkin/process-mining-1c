from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from process_mining.api import create_app
from process_mining.conformance import *
from process_mining.domain import Event
from process_mining.engine import export_report, generate
from process_mining.exports import *
from process_mining.mining import *
from process_mining.normalization import *


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


def test_default_dataset_is_10k_plus_deterministic():
    assert len(generate()) >= 10000 and [x.event_id for x in generate()[:5]] == [
        x.event_id for x in generate()[:5]
    ]


def test_graph_json_and_text_exports():
    events = [ev(1, "c", 1, "A"), ev(2, "c", 2, "B")]
    assert (
        graph_json(events)["edges"]
        and "flowchart LR" in mermaid(events)
        and "digraph process" in dot(events)
    )


def test_report_has_all_analytics():
    assert {
        "variants",
        "bottlenecks",
        "conformance",
        "automation",
        "graph",
    } <= export_report(generate(2)).keys()


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
