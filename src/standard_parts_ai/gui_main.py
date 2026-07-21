# -*- coding: utf-8 -*-
"""纯 GUI 入口，用于 PyInstaller 打包为双击运行的 exe."""

import os
import sys
from pathlib import Path


# PyInstaller 打包后，需要把 casadi 目录加入 DLL 搜索路径，
# 否则 _casadi.pyd 会 DLL load failed.
def _setup_casadi_path() -> None:
    """在运行时确保 casadi 的二进制依赖能被找到."""
    if getattr(sys, "frozen", False):
        # PyInstaller 运行环境：exe 所在目录 / _internal / casadi
        exe_dir = Path(sys.executable).parent
        candidates = [
            exe_dir / "casadi",
            exe_dir / "_internal" / "casadi",
            exe_dir / ".." / "casadi",
        ]
        for casadi_dir in candidates:
            if casadi_dir.exists():
                os.environ["PATH"] = str(casadi_dir) + os.pathsep + os.environ.get("PATH", "")
                # 老版本 Python 用 add_dll_directory
                try:
                    os.add_dll_directory(str(casadi_dir))
                except Exception:  # noqa: BLE001
                    pass
                break


_setup_casadi_path()

from standard_parts_ai.app import main as run_gui


def main() -> None:
    run_gui()


if __name__ == "__main__":
    main()
