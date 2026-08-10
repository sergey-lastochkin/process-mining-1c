"""Streaming XES reader for public process-mining studies."""

from __future__ import annotations

import gzip
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from .domain import Event


@dataclass(slots=True)
class XesLoadReport:
    traces_seen: int = 0
    events_seen: int = 0
    events_loaded: int = 0
    skipped_without_case: int = 0
    skipped_without_activity: int = 0
    skipped_without_timestamp: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def attributes(element: ElementTree.Element) -> dict[str, str]:
    return {
        child.attrib["key"]: child.attrib["value"]
        for child in element
        if "key" in child.attrib and "value" in child.attrib
    }


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def load_xes(path: Path, source_id: str) -> tuple[list[Event], XesLoadReport]:
    """Load XES traces without committing source records to repository files."""
    opener = gzip.open if path.suffix == ".gz" else open
    events: list[Event] = []
    report = XesLoadReport()
    with opener(path, "rb") as handle:
        for _, trace in ElementTree.iterparse(handle, events=("end",)):
            if not trace.tag.endswith("trace"):
                continue
            report.traces_seen += 1
            trace_attributes = attributes(trace)
            case_id = trace_attributes.get("concept:name", "").strip()
            if not case_id:
                report.skipped_without_case += sum(
                    child.tag.endswith("event") for child in trace
                )
                trace.clear()
                continue
            for event_element in (child for child in trace if child.tag.endswith("event")):
                report.events_seen += 1
                data = attributes(event_element)
                action = data.get("concept:name", "").strip()
                if not action:
                    report.skipped_without_activity += 1
                    continue
                occurred_at = data.get("time:timestamp", "")
                if not occurred_at:
                    report.skipped_without_timestamp += 1
                    continue
                try:
                    parsed_at = timestamp(occurred_at)
                except ValueError:
                    report.skipped_without_timestamp += 1
                    continue
                report.events_loaded += 1
                events.append(
                    Event(
                        event_id=f"{source_id}:{report.events_seen}",
                        case_id=case_id,
                        timestamp=parsed_at,
                        user_id=data.get("org:resource", "unknown"),
                        action=action,
                        object_type="XES trace",
                        object_ref=case_id,
                    )
                )
            trace.clear()
    return events, report
