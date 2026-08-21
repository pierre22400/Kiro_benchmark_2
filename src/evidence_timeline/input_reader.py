"""Safe, incremental access to a local UTF-8 JSONL input or standard input."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TextIO


class LocalIOFailure(Exception):
    """The requested local input cannot be opened or decoded safely."""


class PhysicalLine:
    """A decoded physical input line without its CRLF/LF terminator."""

    __slots__ = ("number", "text")

    def __init__(self, number: int, text: str) -> None:
        self.number = number
        self.text = text


def _has_symlink_component(path: Path) -> bool:
    """Return whether an existing component is a symbolic link."""
    current = path
    while True:
        if current.is_symlink():
            return True
        if current.parent == current:
            return False
        current = current.parent


def _validated_file(path_text: str) -> Path:
    path = Path(path_text)
    if _has_symlink_component(path):
        raise LocalIOFailure(path_text)
    try:
        if not path.is_file():
            raise LocalIOFailure(path_text)
    except OSError as error:
        raise LocalIOFailure(path_text) from error
    return path


def iter_input_lines(input_path: str, stdin: TextIO) -> Iterator[PhysicalLine]:
    """Yield UTF-8 physical lines lazily, rejecting unsafe local input paths.

    ``stdin`` is selected only for the exact operand ``-``. File reads use newline
    preservation so either CRLF or LF is stripped once while other characters stay
    intact. UTF-8 decode errors are mapped to ``LocalIOFailure``.
    """
    if input_path == "-":
        yield from _iter_text_lines(stdin)
        return

    path = _validated_file(input_path)
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            yield from _iter_text_lines(handle)
    except (OSError, UnicodeError) as error:
        raise LocalIOFailure(input_path) from error


def _iter_text_lines(handle: TextIO) -> Iterator[PhysicalLine]:
    try:
        for number, raw_line in enumerate(handle, start=1):
            if raw_line.endswith("\r\n"):
                text = raw_line[:-2]
            elif raw_line.endswith("\n"):
                text = raw_line[:-1]
            else:
                text = raw_line
            yield PhysicalLine(number, text)
    except UnicodeError as error:
        raise LocalIOFailure("-") from error
