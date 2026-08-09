"""Small explicit in-memory repository for the local control API."""

from __future__ import annotations

from .domain import Event, ProcessDefinition


class ProcessRepository:
    def __init__(self) -> None:
        self._events: dict[str, list[Event]] = {}
        self._processes: dict[str, ProcessDefinition] = {}

    def create_process(self, process: ProcessDefinition) -> None:
        self._processes[process.process_id] = process
        self._events.setdefault(process.process_id, [])

    def add_events(self, process_id: str, events: list[Event]) -> int:
        if process_id not in self._processes:
            raise KeyError(process_id)
        self._events[process_id].extend(events)
        return len(events)

    def process(self, process_id: str) -> ProcessDefinition:
        return self._processes[process_id]

    def events(self, process_id: str) -> list[Event]:
        return list(self._events[process_id])

    def processes(self) -> list[ProcessDefinition]:
        return list(self._processes.values())
