"""One-shot domain operations with logical results and no stream output."""

from __future__ import annotations

from typing import TextIO

from .contracts import Failure, OperationResult, Request, ValidationPayload, schema_payload
from .input_reader import LocalIOFailure, iter_input_lines
from .jsonl_parser import parse_record
from .timeline import explain, summarize


def execute(request: Request, stdin: TextIO) -> OperationResult | Failure:
    """Execute exactly one normalized request without rendering or output writing."""
    if request.command == "schema":
        return OperationResult(schema_payload(), 0)
    if request.input_path is None:
        return Failure(code="usage")
    if request.command == "validate":
        return _validate(request.input_path, stdin)
    events_or_failure = _load_fail_fast(request.input_path, stdin)
    if isinstance(events_or_failure, Failure):
        return events_or_failure
    if request.command == "summarize":
        return OperationResult(summarize(events_or_failure, request.filters), 0)
    if request.event_id is None:
        return Failure(code="usage")
    explained = explain(events_or_failure, request.event_id)
    if isinstance(explained, Failure):
        return explained
    return OperationResult(explained, 0)


def _validate(input_path: str, stdin: TextIO) -> OperationResult | Failure:
    errors = []
    records = 0
    seen: set[str] = set()
    try:
        for line in iter_input_lines(input_path, stdin):
            parsed = parse_record(line, seen)
            if hasattr(parsed, "code"):
                errors.append(parsed)
            else:
                records += 1
    except LocalIOFailure:
        return Failure(code="local-io")
    return OperationResult(ValidationPayload(tuple(errors), records, not errors), 0 if not errors else 1)


def _load_fail_fast(input_path: str, stdin: TextIO) -> list | Failure:
    events = []
    seen: set[str] = set()
    try:
        for line in iter_input_lines(input_path, stdin):
            parsed = parse_record(line, seen)
            if hasattr(parsed, "code"):
                return Failure(code="invalid-jsonl", line=parsed.line, record_error=parsed.code)
            events.append(parsed)
    except LocalIOFailure:
        return Failure(code="local-io")
    return events
