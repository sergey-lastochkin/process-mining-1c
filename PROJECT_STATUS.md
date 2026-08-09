# Project status

## IMPLEMENTED

Synthetic 10k+ event generator; normalization/dedupe/conflict handling; pseudonymization; explicit case correlation; trace/variant/frequency/cycle p50/p95/rework/bottleneck analysis; conformance checks; automation scoring; JSON/Mermaid/DOT graph output; in-memory repository; exact FastAPI endpoints.

## TESTED

Python 3.12 deterministic unit/API suite, 12k-event smoke, NetworkX graph path and native export validation.

## NOT TESTED

Live 1C journals, production volumes, durable database, authentication, scheduling and a privacy/legal assessment.

## EXTERNAL DEPENDENCIES

Python 3.12+, FastAPI/Pydantic; NetworkX is optional for graph enrichment.

## KNOWN LIMITATIONS

Case IDs must be supplied by a trusted correlation rule. Local repository state is not durable. Candidate score weights are examples requiring domain calibration.

## NEXT PRODUCTION STEPS

Define event contracts and case rules for a target process, persist immutable logs, implement incremental mining, retention/access policy, process-owner validation and dashboards over accepted metrics.
