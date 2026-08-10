"""Render SVG reports from the aggregate BPI Challenge 2012 result JSON."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path


def write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def svg(width: int, height: int, content: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>text {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; fill: #172033; }} .title {{ font-size: 17px; font-weight: 650; }} .label {{ font-size: 12px; fill: #42526e; }} .edge {{ stroke: #8aa0c2; stroke-width: 1.4; opacity: .7; }} .node {{ fill: #f7faff; stroke: #375a90; stroke-width: 1.3; }} .node-text {{ font-size: 11px; text-anchor: middle; }} </style>
<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#8aa0c2"/></marker></defs>{content}</svg>\n'''


def process_map(data: dict[str, object]) -> str:
    summary = data["summary"]
    edges = data["process_map"]["edges"]
    counts: dict[str, int] = {}
    for edge in edges:
        counts[edge["from"]] = counts.get(edge["from"], 0) + edge["frequency"]
        counts[edge["to"]] = counts.get(edge["to"], 0) + edge["frequency"]
    nodes = sorted(counts, key=lambda name: (-counts[name], name))[:18]
    layout = {
        node: (
            520 + 355 * math.cos(2 * math.pi * index / max(1, len(nodes))),
            395 + 265 * math.sin(2 * math.pi * index / max(1, len(nodes))),
        )
        for index, node in enumerate(nodes)
    }
    visible_edges = [
        edge
        for edge in sorted(edges, key=lambda item: -item["frequency"])
        if edge["from"] in layout and edge["to"] in layout
    ][:32]
    edge_svg = "".join(
        f'<line class="edge" x1="{layout[edge["from"]][0]:.0f}" y1="{layout[edge["from"]][1]:.0f}" x2="{layout[edge["to"]][0]:.0f}" y2="{layout[edge["to"]][1]:.0f}" marker-end="url(#arrow)"/>'
        for edge in visible_edges
    )
    node_svg = "".join(
        f'<circle class="node" cx="{x:.0f}" cy="{y:.0f}" r="42"/>'
        f'<text class="node-text" x="{x:.0f}" y="{y - 3:.0f}">{html.escape(node[:18])}</text>'
        f'<text class="label" text-anchor="middle" x="{x:.0f}" y="{y + 14:.0f}">{counts[node]}</text>'
        for node, (x, y) in layout.items()
    )
    title = (
        "BPI Challenge 2012: directly-follows map "
        f"({summary['activities']} activities, {summary['directly_follows_edges']} edges)"
    )
    note = "Shown: 18 highest-degree activities and 32 most frequent connections. Labels below nodes are incident frequencies."
    return svg(
        1040,
        740,
        f'<text class="title" x="30" y="32">{html.escape(title)}</text>'
        f'<text class="label" x="30" y="56">{html.escape(note)}</text>' + edge_svg + node_svg,
    )


def bar_chart(data: dict[str, object]) -> str:
    variants = data["top_variants"][:8]
    bottlenecks = data["top_bottlenecks"][:8]
    maximum_variant = max((item["frequency"] for item in variants), default=1)
    maximum_wait = max((item["cycle_p95_seconds"] for item in bottlenecks), default=1)
    content = [
        '<text class="title" x="30" y="30">Варианты и самые длинные переходы</text>',
        '<text class="label" x="30" y="56">Слева: частота варианта. Справа: p95 ожидания между действиями, seconds.</text>',
        '<text class="label" x="30" y="84">Top variants</text>',
        '<text class="label" x="570" y="84">Top p95 waits</text>',
    ]
    for index, item in enumerate(variants):
        y = 112 + index * 42
        label = " → ".join(item["path"][:3]) + (" …" if len(item["path"]) > 3 else "")
        width = 380 * item["frequency"] / maximum_variant
        content.extend(
            [
                f'<text class="label" x="30" y="{y}">{html.escape(label)}</text>',
                f'<rect x="30" y="{y + 7}" width="{width:.1f}" height="13" rx="3" fill="#3b82f6"/>',
                f'<text class="label" x="420" y="{y + 19}">{item["frequency"]}</text>',
            ]
        )
    for index, item in enumerate(bottlenecks):
        y = 112 + index * 42
        label = f"{item['from']} → {item['to']}"
        width = 370 * item["cycle_p95_seconds"] / maximum_wait
        content.extend(
            [
                f'<text class="label" x="570" y="{y}">{html.escape(label)}</text>',
                f'<rect x="570" y="{y + 7}" width="{width:.1f}" height="13" rx="3" fill="#e58e26"/>',
                f'<text class="label" x="950" y="{y + 19}">{item["cycle_p95_seconds"]:.0f}</text>',
            ]
        )
    return svg(1040, 480, "".join(content))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.results.read_text())
    write(args.output_dir / "process-map.svg", process_map(data))
    write(args.output_dir / "variants-bottlenecks.svg", bar_chart(data))


if __name__ == "__main__":
    main()
