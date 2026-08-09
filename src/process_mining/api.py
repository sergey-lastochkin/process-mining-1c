from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from .conformance import automation_candidates
from .domain import Event, ProcessDefinition
from .exports import dot
from .mining import bottlenecks, case_metrics, variant_stats
from .repository import ProcessRepository


class EventInput(BaseModel):
    event_id: str
    case_id: str
    timestamp: datetime
    user_id: str
    action: str
    object_type: str = "Document"
    object_ref: str = ""
    duration_ms: int = 0


class EventsRequest(BaseModel):
    process_id: str
    events: list[EventInput]


def create_app(repository: ProcessRepository | None = None) -> FastAPI:
    app = FastAPI(title="1C Process Mining", version="2.0")
    app.state.repository = repository or ProcessRepository()
    if not app.state.repository.processes():
        app.state.repository.create_process(
            ProcessDefinition(
                "sales",
                "Synthetic sales lifecycle",
                ("Order", "Reserve", "Sale", "Invoice", "Payment", "Close"),
            )
        )

    def load(process_id: str) -> tuple[ProcessDefinition, list[Event]]:
        try:
            return app.state.repository.process(
                process_id
            ), app.state.repository.events(process_id)
        except KeyError:
            raise HTTPException(404, detail="process not found")

    @app.post("/events")
    def add_events(request: EventsRequest) -> dict[str, object]:
        try:
            count = app.state.repository.add_events(
                request.process_id, [Event(**x.model_dump()) for x in request.events]
            )
        except KeyError:
            raise HTTPException(404, detail="process not found")
        return {"accepted": count, "process_id": request.process_id}

    @app.get("/processes")
    def processes() -> list[dict[str, object]]:
        return [
            {"id": p.process_id, "name": p.name, "expected_path": p.expected_path}
            for p in app.state.repository.processes()
        ]

    @app.get("/process/{process_id}/variants")
    def variants(process_id: str) -> list[dict[str, object]]:
        _, events = load(process_id)
        return variant_stats(events)

    @app.get("/process/{process_id}/bottlenecks")
    def process_bottlenecks(process_id: str) -> list[dict[str, object]]:
        _, events = load(process_id)
        return bottlenecks(events)

    @app.get("/process/{process_id}/automation-candidates")
    def process_candidates(process_id: str) -> list[dict[str, object]]:
        process, events = load(process_id)
        return automation_candidates(events, list(process.expected_path))

    @app.get("/bottlenecks", include_in_schema=False)
    def bottleneck_list(process_id: str = "sales") -> list[dict[str, object]]:
        return process_bottlenecks(process_id)

    @app.get("/automation-candidates", include_in_schema=False)
    def candidates(process_id: str = "sales") -> list[dict[str, object]]:
        return process_candidates(process_id)

    @app.get("/case/{case_id}")
    def case(case_id: str, process_id: str = "sales") -> dict[str, object]:
        _, events = load(process_id)
        found = next((x for x in case_metrics(events) if x["case_id"] == case_id), None)
        if not found:
            raise HTTPException(404, detail="case not found")
        return found

    @app.get("/process/{process_id}/graph.dot", response_class=PlainTextResponse)
    def graph_dot(process_id: str) -> str:
        _, events = load(process_id)
        return dot(events)

    return app


app = create_app()
