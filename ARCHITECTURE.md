# Architecture

The event log is normalized before analysis; conflicting duplicates stop the run. Pure mining functions consume normalized events and return case, variant and edge evidence. Conformance/scoring are separate policy layers. Exporters depend only on aggregated edges. The API repository owns named process definitions and event collections but does not embed analysis logic.
