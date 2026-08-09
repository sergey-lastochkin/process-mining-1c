"""Input hygiene and correlation rules, kept before mining calculations."""

from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256

from .domain import Event


class DuplicateConflict(ValueError):
    """Raised when one event identifier is reused for different evidence."""


def pseudo(value: str, salt: str = "synthetic-demo") -> str:
    return "u_" + sha256((salt + value).encode()).hexdigest()[:16]


def normalise(events: Iterable[Event], salt: str = "synthetic-demo") -> list[Event]:
    """Same id must represent exactly the same business event; conflicts fail closed."""
    unique: dict[str, Event] = {}
    for event in events:
        fingerprint = (event.case_id, event.timestamp, event.action, event.object_ref)
        if event.event_id in unique:
            old = unique[event.event_id]
            if fingerprint != (old.case_id, old.timestamp, old.action, old.object_ref):
                raise DuplicateConflict(
                    f"event_id {event.event_id} has conflicting payload"
                )
            continue
        unique[event.event_id] = Event(
            **{**event.__dict__, "user_id": pseudo(event.user_id, salt)}
        )
    return sorted(unique.values(), key=lambda e: (e.case_id, e.timestamp, e.event_id))


normalize = normalise


def correlate(events: Iterable[Event]) -> dict[str, list[Event]]:
    """Primary rule: explicit case_id. object_ref is retained as audit evidence, not a hidden join."""
    grouped: dict[str, list[Event]] = {}
    for event in normalise(events):
        grouped.setdefault(event.case_id, []).append(event)
    return grouped


traces = correlate
