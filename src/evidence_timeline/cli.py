"""Command-line adapter.

The public parser and stream behavior are introduced after the domain contracts and
operations are available. Importing this module has no observable side effects.
"""

from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI once.

    This bootstrap implementation intentionally has no command behavior yet. It
    exists solely to establish the import-safe console-script boundary.
    """
    del argv
    return 0
