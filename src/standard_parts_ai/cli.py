# -*- coding: utf-8 -*-
"""命令行入口."""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

from .generators import generate_step
from .image_parser import parse_image
from .models import ScrewParams
from .pdf_parser import parse_pdf
from .standards import (
    default_pitch,
    get_cross_drive_size,
    lookup_gb_standard,
    lookup_iso,
)


def _build_params_from_args(args: argparse.Namespace) -> ScrewParams:
    """从命令行参数构造 ScrewParams（手动模式）."""
    major_d = float(args.thread.upper().replace("M", ""))
    pitch = args.pitch or default_pitch(major_d)
    length = args.length or 12.0
    part_no = args.part_no or f"M{int(major_d) if major_d == int(major_d) else major_d}x{int(length)}"

    head_type = args.head_type or "socket"
    drive_type = args.drive_type or "hex"
    tail_type = args.tail_type or "flat"

    iso = lookup_iso(major_d, head_type)

    return ScrewParams(
        part_no=part_no,
        name="螺丝",
        major_d=major_d,
        pitch=pitch,
        length=length,
        head_d=iso["head_d"],
        head_h=iso["head_h"],
        drive_type=drive_type,
        head_type=head_type,
        tail_type=tail_type,
        hex_size=iso.get("hex", 4.0),
        socket_depth=iso.get("socket_depth", 2.5),
        cross_drive_size=get_cross_drive_size(major_d),
        gb_standard=lookup_gb_standard(head_type, drive_type, tail_type),
    )


def _is_image(path: Path) -> bool:
    """判断文件是否为图片."""
    return path.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")


def run_cli(argv: list[str] | None = None) -> int:
    """命令行主入口."""
    parser = argparse.ArgumentParser(
        description="从 PDF 规格书或图片生成螺丝 STEP 文件（离线可用）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python -m standard_parts_ai "规格书/326010708_Screw;M5x12mm.pdf"
  python -m standard_parts_ai "规格书/*.pdf" --out-dir STEP/
  python -m standard_parts_ai "图片/M1.4x5.jpg" --out-dir STEP/
  python -m standard_parts_ai --thread M5 --pitch 0.8 --length 12 --out-dir STEP/
  python -m standard_parts_ai --thread M5 --length 12 --head-type pan --drive-type cross --out-dir STEP/
""",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="PDF 规格书或图片路径，支持单个文件或通配符（如 '规格书/*.pdf'）",
    )
    parser.add_argument(
        "--out-dir",
        default="STEP",
        help="输出目录，默认当前目录下的 STEP/",
    )
    parser.add_argument(
        "--thread",
        help="手动指定螺纹，例如 M5、M6（与 --length 配合使用时跳过输入文件）",
    )
    parser.add_argument(
        "--pitch",
        type=float,
        help="手动指定螺距，例如 0.8",
    )
    parser.add_argument(
        "--length",
        type=float,
        help="手动指定螺杆长度，例如 12",
    )
    parser.add_argument(
        "--part-no",
        help="手动指定料号",
    )
    parser.add_argument(
        "--head-type",
        choices=["socket", "pan", "round", "countersunk"],
        help="螺丝头型，默认 socket（内六角杯头）",
    )
    parser.add_argument(
        "--drive-type",
        choices=["hex", "cross"],
        help="驱动类型，默认 hex（内六角）",
    )
    parser.add_argument(
        "--tail-type",
        choices=["flat", "sharp"],
        help="尾部类型，默认 flat（平尾）",
    )

    args = parser.parse_args(argv)

    # 手动模式
    if args.thread:
        params = _build_params_from_args(args)
        out_path = generate_step(params, Path(args.out_dir))
        print(params)
        print(f"[OK] Generated: {out_path}")
        return 0

    # 输入文件模式
    if not args.input:
        parser.print_help()
        return 1

    paths = glob.glob(args.input)
    if not paths:
        print(f"找不到文件: {args.input}")
        return 1

    out_dir = Path(args.out_dir)
    for path_str in paths:
        path = Path(path_str)
        try:
            if _is_image(path):
                params = parse_image(path)
            else:
                params = parse_pdf(path)
            # 允许命令行覆盖类型
            if args.head_type:
                params.head_type = args.head_type
            if args.drive_type:
                params.drive_type = args.drive_type
            if args.tail_type:
                params.tail_type = args.tail_type
            out_path = generate_step(params, out_dir)
            print(params)
            print(f"[OK] Generated: {out_path}\n")
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {path}: {exc}")

    return 0
