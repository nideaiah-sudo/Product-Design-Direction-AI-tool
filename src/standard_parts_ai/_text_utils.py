# -*- coding: utf-8 -*-
"""纯文本工具函数，供 pdf_parser 与 image_parser 共用."""

from __future__ import annotations


def normalize_text(text: str) -> str:
    """统一文本中的分隔符和符号，便于正则匹配."""
    return (
        text.replace("×", "x")
        .replace("X", "x")
        .replace("*", "x")
        .replace("−", "-")
        .replace("＋", "+")
    )
