"""One-record JSONL parsing and Event validation without stream I/O."""

from __future__ import annotations

import json
from typing import Any

from .contracts import Event, RecordError, RecordErrorCode, SEVERITIES, Severity
from .input_reader import PhysicalLine
from .timestamps import InvalidTimestamp, normalize_timestamp

_REQUIRED_KEYS = {"event_id", "case_id", "timestamp", "severity", "actor", "message", "tags"}


def _invalid_constant(value: str) -> None:
    raise ValueError(value)


def _error(code: RecordErrorCode, line: int) -> RecordError:
    return RecordError(code=code, line=line)


def parse_record(line: PhysicalLine, seen_event_ids: set[str]) -> Event | RecordError:
    """Parse one physical line into a complete Event or one public RecordError.

    The caller supplies state for globally unique IDs. It is updated only after a
    structurally valid first occurrence, so duplicate records never become Events.
    """
    if not line.text.strip():
        return _error("blank-line", line.number)
    try:
        value = json.loads(line.text, parse_constant=_invalid_constant)
    except (json.JSONDecodeError, ValueError):
        return _error("invalid-json", line.number)
    if not isinstance(value, dict) or set(value) != _REQUIRED_KEYS:
        return _error("invalid-event", line.number)
    if not _valid_string_fields(value):
        return _error("invalid-event", line.number)

    severity = value["severity"]
    tags = value["tags"]
    if not isinstance(severity, str) or severity not in SEVERITIES:
        return _error("invalid-event", line.number)
    if not _valid_tags(tags):
        return _error("invalid-event", line.number)
    try:
        timestamp, instant = normalize_timestamp(value["timestamp"])
    except InvalidTimestamp:
        return _error("invalid-event", line.number)

    event_id = value["event_id"]
    if event_id in seen_event_ids:
        return _error("duplicate-event-id", line.number)
    seen_event_ids.add(event_id)
    return Event(
        event_id=event_id,
        case_id=value["case_id"],
        timestamp=timestamp,
        instant=instant,
        severity=severity,  # narrowed by membership in the declared tuple
        actor=value["actor"],
        message=value["message"],
        tags=tuple(tags),
    )


def _valid_string_fields(value: dict[str, Any]) -> bool:
    return all(
        isinstance(value[field], str) and bool(value[field])
        for field in ("event_id", "case_id", "timestamp", "actor", "message")
    )


def _valid_tags(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(tag, str) and bool(tag) for tag in value)
        and len(set(value)) == len(value)
    )
