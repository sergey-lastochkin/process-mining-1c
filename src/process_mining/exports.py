"""Graph outputs, with optional networkx enrichment and a dependency-free fallback."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .domain import Event
from .mining import edges


def graph_json(events: Iterable[Event]) -> dict[str, Any]:
    found = edges(events)
    graph = {
        "nodes": sorted({e["from"] for e in found} | {e["to"] for e in found}),
        "edges": found,
        "engine": "fallback",
    }
    try:
        import networkx as nx

        nx_graph = nx.DiGraph()
        nx_graph.add_weighted_edges_from(
            (x["from"], x["to"], x["frequency"]) for x in found
        )
        graph["engine"] = "networkx"
        graph["node_count"] = nx_graph.number_of_nodes()
        graph["edge_count"] = nx_graph.number_of_edges()
    except ImportError:
        pass
    return graph


def mermaid(events: Iterable[Event]) -> str:
    graph = graph_json(events)
    names = {node: f"N{i}" for i, node in enumerate(graph["nodes"])}
    return "\n".join(
        ["flowchart LR"]
        + [f"  {names[node]}[{node}]" for node in graph["nodes"]]
        + [
            f"  {names[e['from']]} -->|{e['frequency']}| {names[e['to']]}"
            for e in graph["edges"]
        ]
    )


def dot(events: Iterable[Event]) -> str:
    return (
        "digraph process {\n"
        + "\n".join(
            f'  "{e["from"]}" -> "{e["to"]}" [label="{e["frequency"]}"];'
            for e in edges(events)
        )
        + "\n}"
    )
