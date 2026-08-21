# Design — Evidence Timeline CLI

## 1. Design commitments

This design implements [`requirements.md`](./requirements.md) and the resolved v3 [`specblock`](./specblock). It is a Python 3.11+, standard-library-only, one-shot local CLI. It has no stateful service, database, cache, plugin system, global configuration, network access, subprocess, or import-time side effect.

The public executable is `evidence-timeline`. The package is `evidence_timeline`. All business APIs return typed logical values or declared typed failures; they never write stdout/stderr. The CLI adapter alone parses arguments, selects help, emits streams, maps exit codes, and delegates authorized file output.

## 2. Proposed package layout

```text
src/evidence_timeline/
  __init__.py          # metadata only; no I/O
  __main__.py          # invokes cli.main only when executed as a module
  cli.py               # argparse surface, request normalization, exit/stream mapping
  contracts.py         # frozen domain/request/result/failure dataclasses and payload aliases
  timestamps.py        # RFC3339 validation, UTC normalization, comparison instant
  input_reader.py      # safe local/stdin byte-stream opening and physical-line iteration
  jsonl_parser.py      # one-record parsing, Event construction, RecordError preservation
  operations.py        # validate, summarize, explain, schema application operations
  timeline.py          # filters, Event Order, CaseSummary and ExplainPayload construction
  redaction.py         # ordered text-only substitutions
  rendering.py         # canonical JSON and exact text rendering
  output_writer.py     # target preflight and authorized atomic UTF-8 file write
```

`tests/` is planned only after implementation modules exist. No source module is generated in this phase.

## 3. Ownership and execution flow

### 3.1 Request and result flow

```text
argv
  -> cli.parse_argv
  -> contracts.Request
  -> output_writer.preflight_target (only when --output is selected)
  -> operations.execute
       -> input_reader.open_input (except schema)
       -> jsonl_parser.iter_records
       -> timestamps.normalize_timestamp
       -> timeline / schema payload construction
  -> rendering.render
       -> redaction.redact_text_values (only text summarize/explain with --redact)
  -> output_writer.write_atomic (only after complete result rendering)
  -> cli.emit_stdout_or_stderr_and_return_exit_code
```

For `validate`, `operations.execute` consumes all records and constructs `ValidationPayload`. For `summarize` and `explain`, it stops consuming immediately after the first invalid physical line. `schema` never opens an input source.

`output_writer.preflight_target` runs before opening input, so `invalid-output-target` wins over all later observable non-usage failures. No missing directory is created until a complete successful result is rendered and encoded. Rendering precedes file opening/creation. File writes occur only through `write_atomic`.

### 3.2 Failure flow

```text
usage failure              cli -> stderr "error: usage\n", exit 2
invalid output target      preflight_target -> stderr mapping, exit 1
input local I/O            input_reader -> stderr mapping, exit 1
invalid summarize/explain  operations -> stderr mapping, exit 1
event not found            operations -> stderr mapping, exit 1
output local I/O           write_atomic -> stderr mapping, exit 1
invalid validate records   operations -> rendered payload, exit 1
```

Failures are logical contracts, not raised uncaught exceptions. The CLI maps each declared `FailureCode` to its exact public line. Unexpected internal exceptions are caught only at the outermost CLI boundary and converted to the contractually permitted short `error: local-io\n` only if they correspond to an anticipated local I/O boundary; otherwise they are defects and must be exposed to tests rather than silently reclassified.

## 4. Shared contracts

`contracts.py` is the sole producer of shared names and shapes. Frozen dataclasses prevent accidental in-place mutation.

| Contract | Logical fields / invariant | Used by |
| --- | --- | --- |
| `Event` | exact raw event strings, tags tuple, normalized timestamp string, timezone-aware comparison instant | parser, timeline, rendering |
| `EventView` | `actor`, `case_id`, `event_id`, `message`, `severity`, ordered `tags`, normalized `timestamp` | timeline, rendering |
| `RecordError` | exactly `code`, one-based `line`; codes are the four public values | parser, operations, rendering |
| `ValidationPayload` | `errors`, `records`, `valid` | operations, rendering |
| `SummaryPayload` / `CaseSummary` | exact case/event/count shapes; all five severity keys | timeline, rendering |
| `ExplainPayload` | `case_id`, ordered local events, `target_event_id` | timeline, rendering |
| `SchemaPayload` | constant exact public schema | operations, rendering |
| `Request` | command, input selector where required, format, filters, event ID, redact boolean, optional output path, start cwd | cli, operations, writer |
| `Failure` | public failure code plus line/error-code details only where required | reader, operations, writer, cli |
| `OperationResult` | payload and logical exit status (0 or validation-only 1) | operations, rendering, cli |
| `OutputPlan` | prevalidated absolute target and parent-chain facts; no creation yet | writer, cli |

Payload-to-dictionary conversion resides beside these contracts and is used by both renderers. It builds only exact public fields; `rendering.canonical_json` then applies key sorting. This prevents incompatible per-command schemas.

## 5. Module interface inventory

Every interface below records producer, consumer, action, parameters, returned logical value, expected failures, and filesystem effect.

| Producer → consumer | Action and parameters | Return value | Expected failures | Filesystem effect |
| --- | --- | --- | --- | --- |
| `cli` → `contracts` | `normalize_args(namespace, cwd)` | `Request` | usage handled in `cli`; never domain failure | none |
| `output_writer` → `cli` | `preflight_target(output_path, cwd)` | `OutputPlan` or `Failure(INVALID_OUTPUT_TARGET)` | invalid directory/symlink/symlink ancestor | inspection only; no mutation |
| `input_reader` → `operations` | `open_input(input_selector)` then `iter_physical_lines(handle)` | one decoded physical line at a time with one-based line number | `Failure(LOCAL_IO)` for missing/dir/unreadable/symlink/ancestor/decode | read only; no mutation |
| `timestamps` → `jsonl_parser` | `normalize_timestamp(source: str)` | normalized UTC string and aware instant | `RecordError(INVALID_EVENT)` chosen by parser | none |
| `jsonl_parser` → `operations` | `parse_record(line_number, decoded_line, seen_ids)` | `Event` or one `RecordError` | exactly blank-line, invalid-json, invalid-event, duplicate-event-id | none |
| `operations` → `timeline` | `summarize(events, filters)` | exact `SummaryPayload` | none; input failures resolved first | none |
| `operations` → `timeline` | `explain(events, event_id)` | exact `ExplainPayload` or `Failure(EVENT_NOT_FOUND)` | event-not-found | none |
| `operations` → `contracts` | `schema_payload()` | exact constant `SchemaPayload` | none | none |
| `operations` → `cli` | `execute(request)` | `OperationResult` or `Failure` | local-io, invalid-jsonl, event-not-found | input reads only; no mutation |
| `redaction` → `rendering` | `redact_text_value(value)` | redacted string | none | none |
| `rendering` → `cli` | `render(result, format, redact)` | UTF-8-encodable text without its final LF | none | none |
| `output_writer` → `cli` | `write_atomic(plan, utf8_bytes)` | success or `Failure(LOCAL_IO)` | parent/temp/write/flush/close/replace failures | only authorized parents, temporary sibling, atomic replacement |
| `cli` → process streams | `emit(result_or_failure)` | numeric process exit code | no uncaught expected error | stdout/stderr only |

## 6. Detailed responsibility design

### 6.1 CLI adapter (`cli.py`)

`cli.py` builds an `argparse.ArgumentParser` with `allow_abbrev=False` and exactly the declared commands/options. It supplies a controlled parser error path, so all usage defects are mapped to `error: usage\n` rather than argparse prose. It guarantees no input operation before successful parsing and preflight.

The adapter performs these ordered actions: (1) detect no args/help without constructing a domain request; (2) parse; (3) normalize a `Request`; (4) preflight an optional output target; (5) invoke exactly one operation; (6) render only a success or validate-invalid payload; (7) emit stdout or delegate the already rendered bytes to the writer; (8) map a logical result/failure to the exact exit code and stream. It never validates JSONL, compares timestamps, filters events, redacts, or builds payloads.

### 6.2 Input and parsing (`input_reader.py`, `jsonl_parser.py`, `timestamps.py`)

`input_reader.py` is the only owner of input filesystem/stdin access. It rejects prohibited links before opening, checks every existing ancestor of a file path, and uses incremental UTF-8 decoding so a decode error is `local-io` and no later line is read. It accepts only file paths or `-`; it does not write.

`jsonl_parser.py` consumes one decoded physical line at a time. It identifies blank lines before JSON parsing, installs a JSON constant rejection hook, requires a top-level object, validates exact key set and field types, and calls `timestamps.normalize_timestamp`. It updates the seen-ID set only for structurally valid first occurrences. Thus every invalid line produces exactly one public error code with its original physical line number.

`timestamps.py` validates the exact grammar and real date/time values before returning an aware UTC instant plus normalized public timestamp. Its comparison key is never source-text order.

### 6.3 Operations (`operations.py`)

The operation layer orchestrates parsing with no stream output:

- `validate`: iterate to end; collect all `RecordError`s; count valid `Event`s; return `ValidationPayload` with status 0/1.
- `summarize`: iterate until end or first error; convert a first error into `INVALID_JSONL(line, code)`; otherwise pass events/filters to `timeline.summarize`.
- `explain`: same fail-fast read; then call `timeline.explain`.
- `schema`: return the constant payload and never call input APIs.

The input may be read only once for an invocation. The operation layer does not inspect output paths or write a file.

### 6.4 Timeline (`timeline.py`)

The timeline layer uses the `Event` comparison key `(instant, case_id, event_id)` and exact-code-point equality. Summarization applies all filters before grouping, preserves tag input order in views, makes all severity counts explicit, and sorts cases independently by `case_id`. Explain first selects the validated globally unique ID, then orders only that case and slices at most the immediate neighbours.

### 6.5 Rendering and redaction (`rendering.py`, `redaction.py`)

`rendering.py` maps exact payloads to text or canonical JSON. It adds no trailing newline itself. The CLI appends exactly one LF to a result rendered for stdout or file output. Text formatting has dedicated formatters for validation, summary event lines, explain prefixes, and schema field lines.

`redaction.py` owns precompiled standard-library regexes and applies email, hexadecimal identifier, then long token replacements. It is called only for text summaries/explanations after the domain payload/order is fixed. JSON is never redacted and the CLI rejects the incompatible option combination before input is read.

### 6.6 Output writer (`output_writer.py`)

Preflight resolves relative paths against the captured start cwd and rejects a directory, target symlink, or existing symlink in its ancestor chain without mutation. For a valid plan, `write_atomic` receives only already-encoded complete bytes. It creates missing parents only then, creates a sibling temporary file, writes/flushed/closes it, and uses `os.replace` for an existing regular target. On failure, it preserves an unreplaced target and best-effort removes the temporary sibling. No other module receives output-write capability.

## 7. Interface call graph and implementation order

```text
contracts
  ├─ timestamps ─┐
  ├─ jsonl_parser ── operations ── timeline ── rendering ── cli
  ├─ input_reader ───┘                         └─ redaction ─┘
  └─ output_writer ─────────────────────────────────────────┘
```

The dependency order is: `contracts` → `timestamps` → `jsonl_parser` → `input_reader` → `timeline` → `operations` → `redaction`/`rendering` → `output_writer` → `cli`/entrypoints. Modules sharing `Event`, payload, `Failure`, or output contracts are implemented sequentially. After each implemented module, `docs/interface-inventory.md` will be updated with the concrete function signatures and this call graph, then checkpointed and pushed before a dependent module begins.

## 8. Design validation criteria

Before task generation, the design is valid only if:

1. every command, option, input source, payload, rendering mode, public error, exit status, and mutation policy in requirements has an owner;
2. the interface inventory covers every cross-module action and declares parameters, results, failures, and filesystem effects;
3. no business module emits streams or writes files;
4. output preflight precedes input and atomic writing follows complete rendering;
5. `validate` full-scan and `summarize`/`explain` fail-fast semantics remain separate;
6. the planned dependency order avoids parallel work on shared contracts.
