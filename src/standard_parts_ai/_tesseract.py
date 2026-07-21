# -*- coding: utf-8 -*-
"""Tesseract 命令查找工具，供 OCR 相关模块共用."""

from __future__ import annotations

import sys
from pathlib import Path


def find_tesseract_cmd() -> Path:
    """查找 tesseract.exe 路径.

    兼容开发环境（src/ 同级）与 PyInstaller 打包后（_internal/ 下）的目录结构。
    """
    here = Path(__file__).resolve()
    candidates: list[Path] = [
        # 开发环境：src/../tesseract/tesseract.exe
        here.parent.parent.parent / "tesseract" / "tesseract.exe",
        # PyInstaller onedir：_internal/standard_parts_ai/ 的上一层是 _internal/
        here.parent.parent / "tesseract" / "tesseract.exe",
        # PyInstaller onedir 备用：exe 所在目录下的 _internal/tesseract
        Path(sys.executable).parent / "_internal" / "tesseract" / "tesseract.exe",
        # 系统 PATH 中的 tesseract
        Path("tesseract"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path("tesseract")


def get_tesseract_cmd() -> str:
    """返回可用的 tesseract 命令."""
    cmd = find_tesseract_cmd()
    if cmd.exists():
        return str(cmd)
    return "tesseract"


def ocr_image(image, lang: str = "chi_sim+eng") -> str:
    """对 Pillow 图像运行 Tesseract OCR，返回识别文本."""
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("请先安装依赖: pip install pytesseract") from exc
    pytesseract.pytesseract.tesseract_cmd = get_tesseract_cmd()
    return pytesseract.image_to_string(image, lang=lang, config="--psm 6")
