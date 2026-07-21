# -*- coding: utf-8 -*-
"""PyInstaller 打包脚本 —— 使用 onedir 模式."""

import subprocess
import sys
from pathlib import Path


def _casadi_binary_arg() -> str:
    """返回 _casadi.pyd 的 --add-binary 参数，确保它被放到 casadi 目录下."""
    import casadi

    casadi_dir = Path(casadi.__file__).parent
    pyd = casadi_dir / "_casadi.pyd"
    if not pyd.exists():
        raise FileNotFoundError(f"找不到 _casadi.pyd: {pyd}")
    return f"{pyd};casadi"


def main() -> None:
    """打包为独立 exe（onedir 模式）."""
    here = Path(__file__).parent
    entry = here / "src" / "standard_parts_ai" / "gui_main.py"
    output_name = "standard-parts-ai"

    # 项目内的 tesseract portable
    tesseract_dir = here / "tesseract"
    if not tesseract_dir.exists():
        raise FileNotFoundError(f"找不到 tesseract 目录: {tesseract_dir}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        "--windowed",
        "-y",
        "--name",
        output_name,
        "--collect-all",
        "casadi",
        "--collect-all",
        "cadquery",
        "--add-binary",
        _casadi_binary_arg(),
        "--add-data",
        f"{tesseract_dir};tesseract",
        str(entry),
    ]

    print(f"执行打包命令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"\n打包完成，产物位于: {here / 'dist' / output_name / (output_name + '.exe')}")


if __name__ == "__main__":
    main()
