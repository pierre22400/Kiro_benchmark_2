"""Preflighted, authorized local output writing."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile


class OutputFailure(Exception):
    """Declared local output failure carrying its public category."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OutputPlan:
    target: Path


def preflight_target(output_path: str, start_cwd: str) -> OutputPlan:
    """Resolve and inspect a target without creating or modifying anything."""
    target = Path(output_path)
    if not target.is_absolute():
        target = Path(start_cwd) / target
    target = target.absolute()
    if _has_symlink_component(target) or target.is_dir():
        raise OutputFailure("invalid-output-target")
    return OutputPlan(target=target)


def write_atomic(plan: OutputPlan, data: bytes) -> None:
    """Create allowed parents and atomically replace/write the complete bytes."""
    temporary: Path | None = None
    try:
        plan.target.parent.mkdir(parents=True, exist_ok=True)
        if _has_symlink_component(plan.target) or plan.target.is_dir():
            raise OutputFailure("invalid-output-target")
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{plan.target.name}.", dir=plan.target.parent)
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, plan.target)
        temporary = None
    except OutputFailure:
        raise
    except OSError as error:
        raise OutputFailure("local-io") from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _has_symlink_component(path: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        if current.parent == current:
            return False
        current = current.parent
