# Requirements — Evidence Timeline CLI

## 1. Scope and source of truth

This document derives only from [`specblock`](./specblock), validated against commit `c3a9c34885f07efb10aa44ce6e1658abe60d8140`. It defines the public behavior of a one-shot, local Evidence Timeline CLI. It does not define or permit workspace state, persistence, database, server, network, plugins, global configuration, cache, remote metadata, subprocess execution, or a fifth command.

The implementation target is Python 3.11 or later and the Python standard library only. Importing every application module must have no I/O, stream output, argument parsing, command execution, filesystem mutation, network activity, or subprocess activity.

## 2. Command surface

### R-CLI-001 — Commands

The executable is named `evidence-timeline` and exposes exactly these commands:

| Command | Required operands | Supported options |
| --- | --- | --- |
| `validate` | `INPUT` | `--format {text,json}`, `--output OUTPUT_PATH` |
| `summarize` | `INPUT` | `--format {text,json}`, `--case-id CASE_ID`, `--actor ACTOR`, `--min-severity {debug,info,warning,error,critical}`, one or more `--tag TAG`, `--redact`, `--output OUTPUT_PATH` |
| `explain` | `INPUT`, `--event-id EVENT_ID` | `--format {text,json}`, `--redact`, `--output OUTPUT_PATH` |
| `schema` | none | `--format {text,json}`, `--output OUTPUT_PATH` |

`--format` defaults to `text`; `--output` defaults to absent. Options occur only after their command. The CLI rejects abbreviations, aliases, undeclared options, options on an unsupported command, invalid option values, duplicate non-repeatable options, missing or extra operands, malformed option placement, and unknown commands. `--` ends option parsing.

**Acceptance:** all four commands and only their declared options appear in help and are accepted. Every usage failure writes exactly `error: usage\n` to stderr, writes nothing to stdout, reads no input, and returns 2. `--redact` combined with `--format json` is a usage failure.

### R-CLI-002 — Help and no-argument behavior

No arguments, top-level `--help`, and command-level `--help` return 0, write applicable help only to stdout, write nothing to stderr, read no input, and invoke no domain operation. Top-level help includes `usage:`, `Evidence Timeline CLI`, `--help`, and all four command names. Subcommand help includes its exact stable fragments from the SpecBlock, including `--format` and `--output` where declared.

## 3. Event and input contract

### R-DATA-001 — Event schema

Each valid input record is one JSON object containing exactly these keys and no others: `event_id`, `case_id`, `timestamp`, `severity`, `actor`, `message`, `tags`.

| Field | Requirement |
| --- | --- |
| `event_id` | Non-empty JSON string; globally unique by exact Unicode code-point equality. |
| `case_id` | Non-empty JSON string. |
| `timestamp` | RFC3339 value with uppercase `T` and an explicit `Z` or numeric offset; accepted precision is 0–6 fractional digits. |
| `severity` | Exactly one lowercase string: `debug`, `info`, `warning`, `error`, or `critical`. Ranks are 0–4 in that order. |
| `actor` | Non-empty JSON string. |
| `message` | Non-empty JSON string. |
| `tags` | JSON array of zero or more unique non-empty JSON strings, with uniqueness by exact Unicode equality. |

No field can be null. Values expected to be strings reject booleans, numbers, objects, arrays, and null. Strings are never trimmed, normalized, case-folded, or otherwise rewritten. A timestamp rejects missing offsets, leap seconds, invalid calendar/time values, invalid offsets, and invalid precision. Its normalized representation is UTC `YYYY-MM-DDTHH:MM:SSZ` when microseconds are zero, otherwise UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`.

### R-DATA-002 — JSONL parsing and record errors

`INPUT` is either a local UTF-8 file or `-` for UTF-8 stdin. A record is one physical CRLF- or LF-terminated line, excluding its terminator. Empty or whitespace-only lines are errors, not skipped. Every nonblank line must contain one finite JSON object; invalid JSON, non-object values, and `NaN`, `Infinity`, and `-Infinity` are invalid.

Line numbers are one-based physical line numbers. Record errors are exactly `blank-line`, `invalid-json`, `invalid-event`, and `duplicate-event-id`. Each has the logical shape `{"code": RECORD_ERROR_CODE, "line": LINE_NUMBER}`; errors are ordered by increasing line number.

The first structurally valid occurrence of an `event_id` counts as valid; each subsequent occurrence has `duplicate-event-id` and does not count as valid.

### R-DATA-003 — Input resource failures

A missing path, directory, unreadable file, symbolic link, path through an existing symbolic-link ancestor, or UTF-8 decoding failure is a `local-io` failure. It writes exactly `error: local-io\n` to stderr, writes nothing to stdout, changes no output target, and returns 1.

## 4. Domain operations

### R-OP-001 — Validation

`validate` examines every input line in source order, retains no partial Event from an invalid line, and collects exactly one error per invalid line.

Its exact logical payload is:

```json
{"errors":[{"code":"RECORD_ERROR_CODE","line":LINE_NUMBER}],"records":VALID_EVENT_COUNT,"valid":BOOLEAN}
```

With no errors, the payload is `{"errors":[],"records":VALID_EVENT_COUNT,"valid":true}` and exit code 0. With errors, it has all errors, `valid:false`, emits no stderr diagnostic, and returns 1 after complete rendering or output-file writing.

### R-OP-002 — Deterministic event order and views

An `EventView` has exactly these fields: `actor`, `case_id`, `event_id`, `message`, `severity`, `tags`, `timestamp`; its timestamp is normalized and tags retain input order. Event order is ascending normalized timestamp instant, then ascending exact Unicode `case_id`, then ascending exact Unicode `event_id`, with no locale transformation, normalization, or case-folding.

### R-OP-003 — Summarization

`summarize` first loads valid input. Any supplied filters combine with logical AND before grouping and ordering:

- `--case-id` matches exact `case_id`.
- `--actor` matches exact `actor`.
- `--min-severity` keeps ranks greater than or equal to the requested rank.
- repeated `--tag` keeps events containing every supplied distinct tag by exact Unicode equality.

A `CaseSummary` is exactly `{"case_id":CASE_ID,"events":[EventView],"severity_counts":{"critical":N,"debug":N,"error":N,"info":N,"warning":N}}`; every severity key exists, including zero counts. The successful summary payload is exactly `{"cases":[CaseSummary],"event_count":N}`. Cases sort by `case_id`; events sort by Event Order; `N` is the retained-event count. No retained events returns exactly `{"cases":[],"event_count":0}` and exit code 0.

### R-OP-004 — Explain

`explain` loads valid input and finds the event with exact `event_id`. It returns the target event together with its immediate predecessor and successor in Event Order within the target's case, if they exist. It does not include events from any other case.

The exact payload is `{"case_id":CASE_ID,"events":[EventView],"target_event_id":EVENT_ID}`. It contains one event when the target is alone, otherwise only the target and available adjacent event(s). A valid stream without the requested ID is `error: event-not-found\n` on stderr, no stdout/output mutation, exit 1. Duplicate IDs are invalid input; no duplicate is selected.

### R-OP-005 — Schema

`schema` reads neither a file nor stdin and returns exactly:

```json
{"additional_fields":false,"fields":{"actor":"non-empty string","case_id":"non-empty string","event_id":"non-empty globally unique string","message":"non-empty string","severity":"debug|info|warning|error|critical","tags":"array of unique non-empty strings","timestamp":"RFC3339 timestamp with Z or numeric offset"},"nullable_fields":[],"required":["event_id","case_id","timestamp","severity","actor","message","tags"]}
```

It returns 0.

### R-OP-006 — Fail-fast operations

For `summarize` and `explain`, the first invalid line in source order stops processing after that line. The result is exactly `error: invalid-jsonl:LINE_NUMBER:RECORD_ERROR_CODE\n` on stderr, no stdout, no output-file mutation, and exit 1.

## 5. Rendering and redaction

### R-RENDER-001 — Canonical JSON

JSON output serializes the applicable payload using UTF-8 JSON with `ensure_ascii=False`, `allow_nan=False`, sorted object keys, separators `(',', ':')`, and no serializer-owned trailing newline. The CLI appends exactly one LF newline.

### R-RENDER-002 — Text output

- Valid `validate`: `valid: true\nrecords: N\n`.
- Invalid `validate`: `valid: false\nrecords: N\n` followed by `line LINE_NUMBER: RECORD_ERROR_CODE\n` per error.
- Empty `summarize`: exactly `No events.\n`.
- Nonempty `summarize`: each case has `case CASE_ID (N events)\n`, followed immediately by event lines in Event Order: `NORMALIZED_TIMESTAMP [SEVERITY] EVENT_ID actor=ACTOR tags=TAG_LIST MESSAGE\n`. `TAG_LIST` is `-` for no tags, otherwise input-order comma joins. There are no blank lines between cases.
- `explain`: uses the same event line; target has prefix `> ` and context has prefix `  `.
- `schema`: exactly seven LF-terminated lines, in this order: `event_id`, `case_id`, `timestamp`, `severity`, `actor`, `message`, `tags`, with the descriptions defined in SchemaPayload.

### R-RENDER-003 — Redaction

Without `--redact`, strings are unchanged except for timestamp normalization and declared rendering syntax. With `--redact` and text format, redact `case_id`, `event_id`, `actor`, `message`, and every tag only after filtering, grouping, ordering, lookup, and payload construction. Redaction is unavailable for JSON.

Apply non-overlapping substitutions left-to-right in this order:

1. email regex `(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9.-])` → `[REDACTED_EMAIL]`;
2. hexadecimal identifier regex `(?i)(?<![0-9A-F])[0-9A-F]{16,}(?![0-9A-F])` → `[REDACTED_HEX]`;
3. long token regex `(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{24,}(?![A-Za-z0-9_-])` → `[REDACTED_TOKEN]`.

A redacted case ID is rendered consistently in its summary header and event lines.

## 6. Output target and error precedence

### R-IO-001 — Successful output

Without `--output`, a successful result is emitted only to stdout with exactly one final LF; no filesystem entry is created, modified, replaced, renamed, or removed. With `--output`, fully render and UTF-8 encode first, then write identical result bytes to the target and emit nothing to stdout or stderr.

Resolve a relative target once from invocation-start current working directory. Missing parent directories are created only after input processing and rendering succeed. An existing regular non-symlink target is atomically replaced using a temporary sibling and `os.replace` only after successful temporary write.

### R-IO-002 — Invalid target and write failures

A target that is a directory, symlink, or is reached via an existing symlink ancestor fails with exactly `error: invalid-output-target\n`, with no stdout, no target-tree mutation, and exit 1. Parent creation, temporary writing/flushing/closing, or replacement failure produces exactly `error: local-io\n`, no stdout, and exit 1; an existing target remains intact until replacement completes, and a created temporary sibling is removed when possible.

Where multiple non-usage failures are observable without prohibited operations, choose one in this exact order: invalid output target; input `local-io`; invalid JSONL; event not found; output-write `local-io`.

## 7. Cross-cutting acceptance requirements

All equivalent invocations — identical argv, starting working directory, selected input bytes/stdin bytes, and prior target state — produce identical exit code, stdout bytes, stderr bytes, logical payload, output bytes, and filesystem effects. Successful commands emit no unrelated banner, debug, progress, log, advice, or duplicate result. The input is never modified.

The design phase must assign every requirement to one owner and record every interface’s producer, consumer, action, parameter names/types, return schema, expected failures, and filesystem effects. If an interface has conflicting names, types, schema, ordering, error codes, or effects, design stops for reconciliation before task generation or implementation.
