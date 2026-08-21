"""Ordered text-only redaction helpers."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"(?i)(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9.-])")
_HEX = re.compile(r"(?i)(?<![0-9A-F])[0-9A-F]{16,}(?![0-9A-F])")
_TOKEN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{24,}(?![A-Za-z0-9_-])")


def redact_text_value(value: str) -> str:
    """Apply email, hexadecimal-ID, then long-token redaction in that order."""
    return _TOKEN.sub("[REDACTED_TOKEN]", _HEX.sub("[REDACTED_HEX]", _EMAIL.sub("[REDACTED_EMAIL]", value)))
