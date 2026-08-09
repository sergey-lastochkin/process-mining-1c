"""Immutable event and process domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    event_id: str
    case_id: str
    timestamp: datetime
    user_id: str
    action: str
    object_type: str = "Document"
    object_ref: str = ""
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class ProcessDefinition:
    process_id: str
    name: str
    expected_path: tuple[str, ...]
