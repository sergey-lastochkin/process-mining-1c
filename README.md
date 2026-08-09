# 1C Process Mining

## What

Deterministic process-mining reference implementation over synthetic 1C-like events. It reconstructs cases and variants, measures cycle/transition latency, detects rework and conformance deviations, ranks automation candidates and exports the discovered graph.

## Why

Raw journal rows are unordered and duplicated, and a single average hides tails and variants. Mining must normalize identities, fail closed on conflicting duplicates, correlate cases, preserve ordering evidence and keep LLMs out of the computational core.

## Architecture

- Domain records and process definitions.
- Normalization: event-ID dedupe/conflict detection, timestamp ordering and pseudonymization.
- Mining: case traces, variants/frequency, p50/p95, rework and bottlenecks.
- Conformance and deterministic automation-candidate scoring.
- JSON, Mermaid and Graphviz DOT exporters using NetworkX when installed, with native fallback.
- In-memory process repository and FastAPI query surface.

## Key engineering decisions

- Duplicate IDs with different content raise an explicit conflict.
- Case identity is supplied by a correlation contract, never guessed from timestamp proximity.
- Percentiles are calculated from sorted empirical samples.
- Pseudonymization is deterministic but is not claimed as anonymization.
- The default seeded generator emits more than 10,000 synthetic functional-demo events across multiple variants; it is not a load benchmark.

## Run

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/uvicorn process_mining.api:app
```

API: `POST /events`, `GET /processes`, `GET /process/{id}/variants`, `GET /process/{id}/bottlenecks`, `GET /process/{id}/automation-candidates`, `GET /case/{id}`.

Optional NetworkX enrichment is not required because JSON/Mermaid/DOT have a native fallback:

```bash
.venv/bin/python -m pip install -e '.[graphs]'
```

## Test

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

Tests cover duplicates/conflicts, out-of-order events, correlation, variants, p50/p95, rework, bottlenecks, conformance, scoring bounds, 10k+ generation, all exports and exact API semantics.

## Limitations

- Repository state is local/in-memory; no live 1C connector, auth or scheduler is supplied.
- Hash pseudonymization does not satisfy an anonymization or retention policy by itself.
- Automation scores are transparent heuristics, not measured ROI predictions.
