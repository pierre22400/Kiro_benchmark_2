"""Immutable shared contracts for the Evidence Timeline CLI.

All public payload dictionaries are constructed here so every operation shares one
schema. This module is deliberately free of I/O and CLI concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

Severity: TypeAlias = Literal["debug", "info", "warning", "error", "critical"]
OutputFormat: TypeAlias = Literal["text", "json"]
Command: TypeAlias = Literal["validate", "summarize", "explain", "schema"]
RecordErrorCode: TypeAlias = Literal[
    "blank-line", "invalid-json", "invalid-event", "duplicate-event-id"
]
FailureCode: TypeAlias = Literal[
    "usage", "local-io", "invalid-output-target", "invalid-jsonl", "event-not-found"
]

SEVERITY_RANK: dict[Severity, int] = {
    "debug": 0,
    "info": 1,
    "warning": 2,
    "error": 3,
    "critical": 4,
}
SEVERITIES: tuple[Severity, ...] = tuple(SEVERITY_RANK)


@dataclass(frozen=True)
class Event:
    """A fully validated event with a normalized timestamp and sort instant."""

    event_id: str
    case_id: str
    timestamp: str
    instant: datetime
    severity: Severity
    actor: str
    message: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class EventView:
    """The exact public event representation used in result payloads."""

    actor: str
    case_id: str
    event_id: str
    message: str
    severity: Severity
    tags: tuple[str, ...]
    timestamp: str


@dataclass(frozen=True)
class RecordError:
    """One public error associated with a physical JSONL line."""

    code: RecordErrorCode
    line: int


@dataclass(frozen=True)
class CaseSummary:
    """A deterministic case timeline and its complete severity counts."""

    case_id: str
    events: tuple[EventView, ...]
    severity_counts: dict[Severity, int]


@dataclass(frozen=True)
class ValidationPayload:
    errors: tuple[RecordError, ...]
    records: int
    valid: bool


@dataclass(frozen=True)
class SummaryPayload:
    cases: tuple[CaseSummary, ...]
    event_count: int


@dataclass(frozen=True)
class ExplainPayload:
    case_id: str
    events: tuple[EventView, ...]
    target_event_id: str


@dataclass(frozen=True)
class SchemaPayload:
    additional_fields: bool
    fields: dict[str, str]
    nullable_fields: tuple[str, ...]
    required: tuple[str, ...]


PublicPayload: TypeAlias = ValidationPayload | SummaryPayload | ExplainPayload | SchemaPayload


@dataclass(frozen=True)
class Filters:
    case_id: str | None = None
    actor: str | None = None
    min_severity: Severity | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Request:
    command: Command
    input_path: str | None
    output_format: OutputFormat
    output_path: str | None
    filters: Filters = Filters()
    event_id: str | None = None
    redact: bool = False
    start_cwd: str | None = None


@dataclass(frozen=True)
class Failure:
    """A declared, non-streaming expected failure."""

    code: FailureCode
    line: int | None = None
    record_error: RecordErrorCode | None = None


@dataclass(frozen=True)
class OperationResult:
    """A complete logical payload plus its contractual process status."""

    payload: PublicPayload
    exit_code: int


def event_view(event: Event) -> EventView:
    """Return the public view while preserving validated values and tag order."""
    return EventView(
        actor=event.actor,
        case_id=event.case_id,
        event_id=event.event_id,
        message=event.message,
        severity=event.severity,
        tags=event.tags,
        timestamp=event.timestamp,
    )


def record_error_dict(error: RecordError) -> dict[str, object]:
    """Produce the exact public RecordError shape."""
    return {"code": error.code, "line": error.line}


def event_view_dict(view: EventView) -> dict[str, object]:
    """Produce the exact public EventView shape."""
    return {
        "actor": view.actor,
        "case_id": view.case_id,
        "event_id": view.event_id,
        "message": view.message,
        "severity": view.severity,
        "tags": list(view.tags),
        "timestamp": view.timestamp,
    }


def payload_dict(payload: PublicPayload) -> dict[str, object]:
    """Convert a logical payload into its exact external dictionary schema."""
    if isinstance(payload, ValidationPayload):
        return {
            "errors": [record_error_dict(error) for error in payload.errors],
            "records": payload.records,
            "valid": payload.valid,
        }
    if isinstance(payload, SummaryPayload):
        return {
            "cases": [
                {
                    "case_id": case.case_id,
                    "events": [event_view_dict(event) for event in case.events],
                    "severity_counts": dict(case.severity_counts),
                }
                for case in payload.cases
            ],
            "event_count": payload.event_count,
        }
    if isinstance(payload, ExplainPayload):
        return {
            "case_id": payload.case_id,
            "events": [event_view_dict(event) for event in payload.events],
            "target_event_id": payload.target_event_id,
        }
    return {
        "additional_fields": payload.additional_fields,
        "fields": dict(payload.fields),
        "nullable_fields": list(payload.nullable_fields),
        "required": list(payload.required),
    }


def schema_payload() -> SchemaPayload:
    """Return the one exact public event-schema payload."""
    return SchemaPayload(
        additional_fields=False,
        fields={
            "actor": "non-empty string",
            "case_id": "non-empty string",
            "event_id": "non-empty globally unique string",
            "message": "non-empty string",
            "severity": "debug|info|warning|error|critical",
            "tags": "array of unique non-empty strings",
            "timestamp": "RFC3339 timestamp with Z or numeric offset",
        },
        nullable_fields=(),
        required=("event_id", "case_id", "timestamp", "severity", "actor", "message", "tags"),
    )
