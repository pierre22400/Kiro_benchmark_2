"""Exact text and canonical JSON rendering without stream I/O."""

from __future__ import annotations

import json

from .contracts import ExplainPayload, PublicPayload, SchemaPayload, SummaryPayload, ValidationPayload, payload_dict
from .redaction import redact_text_value


def render(payload: PublicPayload, output_format: str, redact: bool = False) -> str:
    """Render a complete payload without its one caller-owned final LF."""
    if output_format == "json":
        return json.dumps(payload_dict(payload), ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    if isinstance(payload, ValidationPayload):
        lines = [f"valid: {str(payload.valid).lower()}", f"records: {payload.records}"]
        lines.extend(f"line {error.line}: {error.code}" for error in payload.errors)
        return "\n".join(lines)
    if isinstance(payload, SummaryPayload):
        if not payload.cases:
            return "No events."
        lines: list[str] = []
        for case in payload.cases:
            case_id = _redact(case.case_id, redact)
            lines.append(f"case {case_id} ({len(case.events)} events)")
            lines.extend(_event_line(event, redact, "") for event in case.events)
        return "\n".join(lines)
    if isinstance(payload, ExplainPayload):
        return "\n".join(
            _event_line(event, redact, "> " if event.event_id == payload.target_event_id else "  ")
            for event in payload.events
        )
    return _schema_text(payload)


def _event_line(event: object, redact: bool, prefix: str) -> str:
    # EventView is intentionally structural here to keep this formatter read-only.
    tags = getattr(event, "tags")
    tag_list = "-" if not tags else ",".join(_redact(tag, redact) for tag in tags)
    return (
        f"{prefix}{getattr(event, 'timestamp')} [{getattr(event, 'severity')}] "
        f"{_redact(getattr(event, 'event_id'), redact)} actor={_redact(getattr(event, 'actor'), redact)} "
        f"tags={tag_list} {_redact(getattr(event, 'message'), redact)}"
    )


def _redact(value: str, enabled: bool) -> str:
    return redact_text_value(value) if enabled else value


def _schema_text(payload: SchemaPayload) -> str:
    return "\n".join(
        f"{field}: {payload.fields[field]}"
        for field in ("event_id", "case_id", "timestamp", "severity", "actor", "message", "tags")
    )
