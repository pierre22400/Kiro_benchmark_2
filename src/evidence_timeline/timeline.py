"""Pure deterministic filtering, timeline construction, and event explanation."""

from __future__ import annotations

from collections import defaultdict

from .contracts import (
    CaseSummary,
    Event,
    ExplainPayload,
    Failure,
    Filters,
    SEVERITIES,
    SEVERITY_RANK,
    SummaryPayload,
    event_view,
)


def event_sort_key(event: Event) -> tuple[object, str, str]:
    """Return the one declared Event Order key."""
    return event.instant, event.case_id, event.event_id


def summarize(events: list[Event], filters: Filters) -> SummaryPayload:
    """Filter with AND semantics then construct an exact deterministic summary."""
    retained = [event for event in events if _matches(event, filters)]
    grouped: dict[str, list[Event]] = defaultdict(list)
    for event in retained:
        grouped[event.case_id].append(event)

    cases: list[CaseSummary] = []
    for case_id in sorted(grouped):
        ordered = sorted(grouped[case_id], key=event_sort_key)
        counts = {severity: 0 for severity in SEVERITIES}
        for event in ordered:
            counts[event.severity] += 1
        cases.append(
            CaseSummary(
                case_id=case_id,
                events=tuple(event_view(event) for event in ordered),
                severity_counts=counts,
            )
        )
    return SummaryPayload(cases=tuple(cases), event_count=len(retained))


def explain(events: list[Event], event_id: str) -> ExplainPayload | Failure:
    """Return a target event and at most one ordered neighbour on either side."""
    target = next((event for event in events if event.event_id == event_id), None)
    if target is None:
        return Failure(code="event-not-found")
    case_events = sorted(
        (event for event in events if event.case_id == target.case_id), key=event_sort_key
    )
    index = next(index for index, event in enumerate(case_events) if event.event_id == event_id)
    start = max(0, index - 1)
    end = min(len(case_events), index + 2)
    return ExplainPayload(
        case_id=target.case_id,
        events=tuple(event_view(event) for event in case_events[start:end]),
        target_event_id=event_id,
    )


def _matches(event: Event, filters: Filters) -> bool:
    if filters.case_id is not None and event.case_id != filters.case_id:
        return False
    if filters.actor is not None and event.actor != filters.actor:
        return False
    if filters.min_severity is not None:
        if SEVERITY_RANK[event.severity] < SEVERITY_RANK[filters.min_severity]:
            return False
    required_tags = set(filters.tags)
    return all(tag in event.tags for tag in required_tags)
