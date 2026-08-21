"""Strict RFC3339 timestamp validation and UTC normalization."""

from __future__ import annotations

from datetime import datetime, timezone
import re

_TIMESTAMP_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})T"
    r"(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?P<fraction>\.\d{1,6})?"
    r"(?P<offset>Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)


class InvalidTimestamp(ValueError):
    """Raised when a source timestamp does not satisfy the public grammar."""


def normalize_timestamp(value: str) -> tuple[str, datetime]:
    """Return the canonical UTC value and its timezone-aware comparison instant.

    Accepted values have uppercase ``T`` and ``Z``, an explicit offset, at most six
    fractional digits, and a real Gregorian date/time. Python's datetime parser
    provides date/time validation after the grammar restricts the accepted form.
    """
    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise InvalidTimestamp(value)

    offset = match.group("offset")
    iso_value = value[:-1] + "+00:00" if offset == "Z" else value
    try:
        instant = datetime.fromisoformat(iso_value)
    except ValueError as error:
        raise InvalidTimestamp(value) from error

    if instant.tzinfo is None:
        raise InvalidTimestamp(value)
    utc = instant.astimezone(timezone.utc)
    if utc.microsecond == 0:
        normalized = utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        normalized = utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond:06d}Z"
    return normalized, utc
