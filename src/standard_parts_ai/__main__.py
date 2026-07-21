# -*- coding: utf-8 -*-
"""包入口：支持命令行与 GUI 两种模式."""

import sys

from .cli import run_cli
from .app import main as run_gui


def main() -> int:
    """默认启动 GUI；如果带命令行参数则走 CLI."""
    if len(sys.argv) > 1:
        return run_cli()
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
