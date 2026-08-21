# Concrete Interface Inventory

This inventory is updated and pushed after each implementation module, before a dependent module is started.

## Bootstrap

| Module | Public callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `evidence_timeline.cli` | `main(argv: Sequence[str] | None = None)` | optional process argument vector | process status `int` | none during bootstrap | none |
| `evidence_timeline.__main__` | module execution guard | none | process exit via `SystemExit(main())` only when executed | delegated to `main` | none |

## Current call graph

```text
console script / python -m evidence_timeline
  -> evidence_timeline.cli.main
```

Importing every listed module performs no argument parsing, stream emission, input read, filesystem mutation, network access, or subprocess execution.


## Shared contracts (`contracts.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `contracts` → parser/timeline/rendering/operations | `Event`, `EventView`, `RecordError`, payload dataclasses, `Request`, `Failure`, `OperationResult` | immutable declared fields | one shared logical contract per public schema | none | none |
| `contracts` → rendering | `payload_dict(payload)` | any `PublicPayload` | exact external dictionary shape | none | none |
| `contracts` → operations | `event_view(event)` | validated `Event` | exact `EventView` | none | none |
| `contracts` → operations/rendering | `schema_payload()` | none | exact `SchemaPayload` | none | none |

## Updated call graph

```text
cli (future) -> contracts.Request
operations (future) -> contracts.Event / payload / Failure
parser (future) -> contracts.Event / RecordError
rendering (future) -> contracts.payload_dict
```
