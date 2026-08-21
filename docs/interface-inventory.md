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


## Timestamp normalization (`timestamps.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `timestamps` → `jsonl_parser` | `normalize_timestamp(value: str)` | source timestamp string | `(normalized_utc: str, comparison_instant: datetime)` | `InvalidTimestamp` for every unsupported or unreal date/time form | none |

The normalized string is UTC with zero fractional digits only when the microsecond value is zero; the returned instant is timezone-aware and is the sole timestamp sort component.

## Updated call graph

```text
jsonl_parser (future) -> timestamps.normalize_timestamp -> (normalized UTC string, aware instant)
jsonl_parser (future) -> contracts.Event
```


## Safe input reader (`input_reader.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `input_reader` → `operations` | `iter_input_lines(input_path, stdin)` | local input path or `-`, supplied stdin stream | lazy `PhysicalLine(number, text)` iterator | `LocalIOFailure` for missing/unsafe/unreadable/undecodable local input | input read only; no mutation |

The reader owns local-file and stdin selection. It rejects a symlink target or existing symlink ancestor before opening a local file and strips only CRLF/LF terminators.

## Updated call graph

```text
operations (future) -> input_reader.iter_input_lines -> PhysicalLine
operations (future) -> jsonl_parser.parse_record -> contracts.Event | RecordError
```


## Single-record parser (`jsonl_parser.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `jsonl_parser` → `operations` | `parse_record(line, seen_event_ids)` | one `PhysicalLine`, mutable seen-ID set | one validated `Event` or one `RecordError` | public record codes only: `blank-line`, `invalid-json`, `invalid-event`, `duplicate-event-id` | none |

The parser owns finite-JSON enforcement, exact event-key/type/enum/tag validation, timestamp normalization delegation, and first-valid-ID registration. It never reads streams or emits output.

## Updated call graph

```text
operations (future)
  -> input_reader.iter_input_lines
  -> jsonl_parser.parse_record
       -> timestamps.normalize_timestamp
       -> contracts.Event | contracts.RecordError
```


## Timeline operations (`timeline.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `timeline` → `operations` | `summarize(events, filters)` | validated Events and exact `Filters` | exact `SummaryPayload` | none | none |
| `timeline` → `operations` | `explain(events, event_id)` | validated Events, exact event ID | exact `ExplainPayload` or `Failure(event-not-found)` | event-not-found only | none |

The module owns Event Order, logical-AND filters, complete severity counts, case ordering, and local explain context. It has no input or output capability.

## Updated call graph

```text
operations (future) -> timeline.summarize / timeline.explain
  -> contracts.EventView / SummaryPayload / ExplainPayload / Failure
```


## Text redaction (`redaction.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `redaction` → `rendering` | `redact_text_value(value)` | one already-selected text field | redacted string | none | none |

Redaction applies non-overlapping email, hexadecimal identifier, then long-token replacements. It performs no filtering, lookup, I/O, or JSON rendering.


## Rendering (`rendering.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `rendering` → `cli` | `render(payload, output_format, redact=False)` | exact public payload, `text`/`json`, text-redaction flag | complete result text without final LF | none | none |

JSON uses the shared payload dictionary and canonical serializer settings. Text rendering owns all declared lines. Redaction is called only by text summary/explain formatting after domain ordering.


## Output writer (`output_writer.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `output_writer` → `cli` | `preflight_target(output_path, start_cwd)` | raw requested path, invocation start cwd | immutable `OutputPlan` | `OutputFailure(invalid-output-target)` | inspection only |
| `output_writer` → `cli` | `write_atomic(plan, data)` | preflighted target and complete UTF-8 bytes | none | `OutputFailure(local-io|invalid-output-target)` | authorized parent creation, temporary sibling, atomic replace |

Only this module has output-write capability. The CLI must preflight before input and call writing only after the full result bytes exist.


## Application operations (`operations.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| `operations` → `cli` | `execute(request, stdin)` | normalized `Request`, selected stdin stream | `OperationResult` or logical `Failure` | local-io, invalid-jsonl, event-not-found, usage | input read only |

`validate` scans all records; `summarize` and `explain` stop after the first invalid record; `schema` never accesses input. The module never renders, emits, or writes output.

## Updated call graph

```text
cli (future) -> output_writer.preflight_target -> operations.execute
operations -> input_reader -> jsonl_parser -> timestamps
operations -> timeline -> contracts payload
cli (future) -> rendering -> output_writer.write_atomic | stdout
```


## CLI adapter (`cli.py`)

| Producer → consumer | Callable | Parameters | Return | Expected failures | Filesystem effects |
| --- | --- | --- | --- | --- | --- |
| process → `cli` | `main(argv=None)` | optional argv; process stdin/stdout/stderr | contractual process status | usage, invalid-output-target, local-io, invalid-jsonl, event-not-found | delegates only authorized output writing |

The adapter owns argparse grammar, help, request construction, output preflight, one operation invocation, rendering, stream emission, and exit mapping. It owns no parsing, validation, timeline, redaction, or output-write implementation.

## Final call graph

```text
process -> cli.main
  -> output_writer.preflight_target (optional)
  -> operations.execute -> input_reader -> jsonl_parser -> timestamps
                       -> timeline / schema payload
  -> rendering -> redaction (text summarize/explain only)
  -> stdout OR output_writer.write_atomic
```
