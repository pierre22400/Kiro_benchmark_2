"""Strict command-line adapter for the Evidence Timeline CLI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
import sys
from typing import NoReturn

from .contracts import Filters, Request
from .operations import execute
from .output_writer import OutputFailure, preflight_target, write_atomic
from .rendering import render


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise _UsageError


def _parser() -> _Parser:
    parser = _Parser(prog="evidence-timeline", description="Evidence Timeline CLI", allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True, title="commands")
    _add_common(sub.add_parser("validate", allow_abbrev=False), input_required=True)
    summary = sub.add_parser("summarize", allow_abbrev=False)
    _add_common(summary, input_required=True)
    summary.add_argument("--case-id")
    summary.add_argument("--actor")
    summary.add_argument("--min-severity", choices=("debug", "info", "warning", "error", "critical"))
    summary.add_argument("--tag", action="append", default=[])
    summary.add_argument("--redact", action="store_true")
    explained = sub.add_parser("explain", allow_abbrev=False)
    _add_common(explained, input_required=True)
    explained.add_argument("--event-id", required=True)
    explained.add_argument("--redact", action="store_true")
    _add_common(sub.add_parser("schema", allow_abbrev=False), input_required=False)
    return parser


def _add_common(parser: argparse.ArgumentParser, input_required: bool) -> None:
    if input_required:
        parser.add_argument("input")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one normalized CLI invocation and return its contractual status."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = _parser()
    if not arguments:
        parser.print_help(sys.stdout)
        return 0
    if _has_duplicate_nonrepeat_option(arguments):
        return _usage()
    try:
        namespace = parser.parse_args(arguments)
    except _UsageError:
        return _usage()
    except SystemExit as exit_signal:
        return int(exit_signal.code)
    if getattr(namespace, "redact", False) and namespace.format == "json":
        return _usage()

    request = Request(
        command=namespace.command,
        input_path=getattr(namespace, "input", None),
        output_format=namespace.format,
        output_path=namespace.output,
        filters=Filters(
            case_id=getattr(namespace, "case_id", None),
            actor=getattr(namespace, "actor", None),
            min_severity=getattr(namespace, "min_severity", None),
            tags=tuple(getattr(namespace, "tag", [])),
        ),
        event_id=getattr(namespace, "event_id", None),
        redact=getattr(namespace, "redact", False),
        start_cwd=os.getcwd(),
    )
    plan = None
    if request.output_path is not None:
        try:
            plan = preflight_target(request.output_path, request.start_cwd or os.getcwd())
        except OutputFailure as failure:
            return _failure(failure.code)
    result = execute(request, sys.stdin)
    if hasattr(result, "code"):
        return _failure(result.code, result.line, result.record_error)
    content = render(result.payload, request.output_format, request.redact) + "\n"
    if plan is not None:
        try:
            write_atomic(plan, content.encode("utf-8"))
        except OutputFailure as failure:
            return _failure(failure.code)
    else:
        sys.stdout.write(content)
    return result.exit_code


def _has_duplicate_nonrepeat_option(arguments: list[str]) -> bool:
    options = ("--format", "--output", "--case-id", "--actor", "--min-severity", "--event-id", "--redact")
    return any(sum(argument == option or argument.startswith(option + "=") for argument in arguments) > 1 for option in options)


def _usage() -> int:
    sys.stderr.write("error: usage\n")
    return 2


def _failure(code: str, line: int | None = None, record_error: str | None = None) -> int:
    if code == "invalid-jsonl":
        sys.stderr.write(f"error: invalid-jsonl:{line}:{record_error}\n")
    else:
        sys.stderr.write(f"error: {code}\n")
    return 1
