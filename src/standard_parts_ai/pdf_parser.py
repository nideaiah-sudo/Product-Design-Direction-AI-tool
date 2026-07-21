# -*- coding: utf-8 -*-
"""PDF 规格书解析模块（PDF 专用路径）."""

from __future__ import annotations

import re
from pathlib import Path

from PyPDF2 import PdfReader

from ._tesseract import get_tesseract_cmd, ocr_image
from ._text_utils import normalize_text
from .models import ScrewParams
from .standards import (
    DRIVE_TYPE_MAP,
    HEAD_TYPE_MAP,
    TAIL_TYPE_MAP,
    default_pitch,
    get_cross_drive_size,
    lookup_gb_standard,
    lookup_iso,
)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """从 PDF 提取文本.

    优先使用 PyMuPDF（fitz），它对旋转文字、工程图标注提取更好；
    未安装时回退到 PyPDF2。
    如果提取到的文字过短，再尝试把页面渲染成图片后 OCR（处理扫描件/图片 PDF）。
    """
    full_text = ""

    # 1. 优先使用 PyMuPDF 提取（支持旋转文字）
    try:
        import fitz  # type: ignore[import-untyped]

        doc = fitz.open(pdf_path)
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text())
        full_text = "\n".join(parts)
    except Exception:  # noqa: BLE001
        full_text = ""

    # 2. 回退 PyPDF2
    if not full_text.strip():
        try:
            text_parts: list[str] = []
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            full_text = "\n".join(text_parts)
        except Exception:  # noqa: BLE001
            full_text = ""

    # 3. 扫描型/图片型 PDF 回退：文字太少时渲染页面 OCR
    if len(full_text.strip()) < 30:
        ocr_text = _ocr_pdf_pages(pdf_path)
        if ocr_text.strip():
            full_text = full_text + "\n" + ocr_text if full_text.strip() else ocr_text

    return full_text


def _ocr_pdf_pages(pdf_path: Path) -> str:
    """将 PDF 每页渲染为图片并 OCR，支持 90° 旋转文字.

    需要 ``pymupdf`` 用于渲染，``pytesseract`` 用于 OCR。
    依赖未安装时返回空字符串。
    """
    try:
        import fitz  # type: ignore[import-untyped]
        from PIL import Image, ImageOps
    except Exception:  # noqa: BLE001
        return ""

    try:
        doc = fitz.open(pdf_path)
        ocr_texts: list[str] = []
        for page in doc:
            # 200 dpi 渲染
            mat = fitz.Matrix(200 / 72, 200 / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            # 对每页尝试原图、90°、180°、270° OCR，合并结果
            for angle in (0, 90, 180, 270):
                rotated = img.rotate(angle, expand=True).convert("L")
                rotated = ImageOps.autocontrast(rotated)
                mean_pixel = sum(rotated.getdata()) / (rotated.width * rotated.height)
                if mean_pixel > 128:
                    rotated = ImageOps.invert(rotated)
                ocr_texts.append(ocr_image(rotated, lang="chi_sim+eng"))
        return "\n".join(ocr_texts)
    except Exception:  # noqa: BLE001
        return ""


def _parse_floats(text: str) -> list[float]:
    """从文本中提取所有浮点数."""
    return [float(x) for x in re.findall(r"[-+]?\d*\.?\d+", text)]


def _detect_head_type_pdf(text: str) -> str:
    """从 PDF 文本中识别螺丝头型."""
    lower = text.lower()
    for keyword, head_type in HEAD_TYPE_MAP.items():
        if keyword in lower:
            return head_type
    return "socket"


def _detect_drive_type_pdf(text: str) -> str:
    """从 PDF 文本中识别驱动类型."""
    lower = text.lower()
    for keyword, drive_type in DRIVE_TYPE_MAP.items():
        if keyword in lower:
            return drive_type
    return "hex"


def _detect_tail_type_pdf(text: str) -> str:
    """从 PDF 文本中识别尾部类型."""
    lower = text.lower()
    for keyword, tail_type in TAIL_TYPE_MAP.items():
        if keyword in lower:
            return tail_type
    return "flat"


def _parse_dimension_line_pdf(text: str) -> dict[str, float]:
    """从 PDF 文本解析关键尺寸（PDF 专用）.

    主要识别：螺纹大径、螺距、螺杆长度、头径、头高。
    优先使用带关键字/上下文的模式，减少误匹配。
    """
    result: dict[str, float] = {}
    text = normalize_text(text)

    # 1. 螺纹规格：M5 / M5x0.8 / M5x12 / M5x0.8x12 / M1.4x0.3
    m = re.search(
        r"M\s*(\d+(?:\.\d+)?)(?:\s*x\s*(\d+(?:\.\d+)?))?(?:\s*x\s*(\d+(?:\.\d+)?))?",
        text,
        re.IGNORECASE,
    )
    if m:
        major = float(m.group(1))
        values = [float(g) for g in (m.group(2), m.group(3)) if g is not None]
        if len(values) == 0:
            result["major_d"] = major
            result["pitch"] = default_pitch(major)
        elif len(values) == 1:
            result["major_d"] = major
            if values[0] <= 2.0:
                result["pitch"] = values[0]
            else:
                result["length"] = values[0]
                result["pitch"] = default_pitch(major)
        else:
            result["major_d"] = major
            result["pitch"] = values[0]
            result["length"] = values[1]

    # 2. 螺杆长度：12.0±0.35 / 12.0+0/-0.5 / L=12 / 长度 12 / 螺杆长度 12 / 螺纹长度 12
    len_match = re.search(
        r"(?:L|长度|螺杆长度|螺纹长度)\s*[:=]?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if len_match:
        result["length"] = float(len_match.group(1))
    else:
        # 带公差的长度：10.0+0/-0.5 / 10.0±0.5
        len_values = [
            float(m.group(1))
            for m in re.finditer(
                r"(\d+(?:\.\d+)?)\s*(?:±\s*\d+(?:\.\d+)?|\+\s*\d+(?:\.\d+)?\s*/\s*-\s*\d+(?:\.\d+)?)",
                text,
            )
        ]
        if len_values:
            result["length"] = max(len_values)

    # 3. 头径：∅8.28-∅8.72 / ∅5.5+0.5 / d=8.5 / 头径 8.5 / 头部直径 8.5
    head_d_match = re.search(
        r"(?:头径|头部直径|head\s*d|head\sdia|d\s*=|∅)\s*(\d+(?:\.\d+)?)\s*(?:[-~]\s*(?:∅|d\s*=\s*)?(\d+(?:\.\d+)?)|\s*[+-]\s*\d+(?:\.\d+)?)?",
        text,
        re.IGNORECASE,
    )
    if head_d_match:
        a = float(head_d_match.group(1))
        b = head_d_match.group(2)
        result["head_d"] = (a + float(b)) / 2 if b else a
    else:
        # 弱匹配：d 8.28-8.72 / ∅8.28-8.72
        head_d_match = re.search(
            r"(?:∅|d\s*=)\s*(\d+(?:\.\d+)?)\s*[-~]\s*(?:∅|d\s*=)?\s*(\d+(?:\.\d+)?)",
            text,
        )
        if head_d_match:
            a = float(head_d_match.group(1))
            b = float(head_d_match.group(2))
            result["head_d"] = (a + b) / 2

    # 4. 头高：头高 4.82-5.00 / 头高 5.0 / K 5.0 / 2.0±0.15
    head_h_match = re.search(
        r"(?:头高|头部厚度|head\s*h|head\s*height|K)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:[-~]\s*(\d+(?:\.\d+)?)|\s*±\s*\d+(?:\.\d+)?)?",
        text,
        re.IGNORECASE,
    )
    if head_h_match:
        a = float(head_h_match.group(1))
        b = head_h_match.group(2)
        result["head_h"] = (a + float(b)) / 2 if b else a
    else:
        # Fallback：从 A-B 区间推断头高。
        candidates = []
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", text):
            a, b = float(m.group(1)), float(m.group(2))
            # 跳过线程规格中的区间，例如 M5x0.8-6g / M5X 0.8-6g
            preceding = text[: m.start()].rstrip()
            if preceding and preceding[-1].lower() == "x":
                continue
            # 合理头高范围：0.5 ~ 15 mm
            if 0.5 <= a <= 15.0 and 0.5 <= b <= 15.0:
                candidates.append((a, b))
        if candidates:
            # 取平均值最小的作为头高
            a, b = min(candidates, key=lambda pair: (pair[0] + pair[1]) / 2)
            result["head_h"] = (a + b) / 2
        else:
            # 再尝试从 ± 公差中推断头高（例如 2.0±0.15）
            # 取合理范围（0.5~5.0）内最小的数值
            values = []
            for m in re.finditer(r"(\d+(?:\.\d+)?)\s*±\s*\d+(?:\.\d+)?", text):
                val = float(m.group(1))
                if 0.5 <= val <= 5.0 and val != result.get("length"):
                    values.append(val)
            if values:
                result["head_h"] = min(values)

    return result


def _parse_table_block_pdf(text: str) -> dict[str, float]:
    """尝试从类表格文本块中提取关键尺寸.

    简单启发式：寻找多列对齐的浮点数组，按列名/上下文推断。
    """
    result: dict[str, float] = {}
    lines = [line for line in text.splitlines() if line.strip()]
    for line in lines:
        # 简单匹配 "d x.x" / "k x.x" / "L x.x" 等表格行
        for label, key in (("d", "head_d"), ("k", "head_h"), ("L", "length")):
            # 匹配类似 " d  8.50  " 或 " d=8.5 "
            m = re.search(
                rf"\b{re.escape(label)}\s*[:=]?\s*(\d+(?:\.\d+)?)\b",
                line,
                re.IGNORECASE,
            )
            if m:
                result[key] = float(m.group(1))
    return result


def _parse_filename(pdf_path: Path) -> dict[str, str | float]:
    """从文件名解析料号和规格."""
    result: dict[str, str | float] = {}
    stem = pdf_path.stem
    stem_norm = normalize_text(stem)

    # 料号：下划线前的数字串
    m = re.match(r"(\d+)", stem)
    if m:
        result["part_no"] = m.group(1)

    # 名称：取 "Screw;" 后面的中文描述
    name_match = re.search(r"Screw;\s*([^-]+)-", stem)
    if name_match:
        result["name"] = name_match.group(1).strip()
    else:
        name_match = re.search(r"[_;]([^-]+)-", stem)
        if name_match:
            result["name"] = name_match.group(1).strip()
        else:
            # 尝试取 "Screw;" 后到第一个逗号/规格之前的文本
            name_match = re.search(r"Screw;\s*([^,，]+)", stem)
            if name_match:
                result["name"] = name_match.group(1).strip()
            else:
                result["name"] = stem

    # 规格 M5x12 / M5x0.8x12 / M5x12mm / PB2x6 / PB2x6mm / ST2.9x13mm 等
    # 先尝试三段式 M5x0.8x12 / M5x0.8x12mm
    spec_match = re.search(
        r"(?:[A-Za-z]{0,4}\s*)?M?\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)(?:\s*mm)?",
        stem_norm,
        re.IGNORECASE,
    )
    if spec_match:
        result["major_d"] = float(spec_match.group(1))
        result["pitch"] = float(spec_match.group(2))
        result["length"] = float(spec_match.group(3))
    else:
        # 再尝试两段式 M5x12 / PB2x6 / M5x12mm
        spec_match = re.search(
            r"(?:[A-Za-z]{0,4}\s*)?M?\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)(?:\s*mm)?",
            stem_norm,
            re.IGNORECASE,
        )
        if spec_match:
            result["major_d"] = float(spec_match.group(1))
            result["length"] = float(spec_match.group(2))
            # 根据第二段数值判断是螺距还是长度
            second = result["length"]
            if second <= 2.0:
                result["pitch"] = second
                result["length"] = 12.0  # 缺省长度，后续可被 PDF 覆盖
            else:
                result["pitch"] = default_pitch(result["major_d"])

    # 从文件名识别头型、驱动、尾部
    result["head_type"] = _detect_head_type_pdf(stem)
    result["drive_type"] = _detect_drive_type_pdf(stem)
    result["tail_type"] = _detect_tail_type_pdf(stem)

    return result


def parse_pdf(pdf_path: Path) -> ScrewParams:
    """从 PDF 规格书解析螺丝参数（PDF 专用入口）."""
    text = extract_text_from_pdf(pdf_path)
    pdf_dims = _parse_dimension_line_pdf(text)
    pdf_dims.update(_parse_table_block_pdf(text))
    file_info = _parse_filename(pdf_path)

    part_no = str(file_info.get("part_no", pdf_path.stem))
    name = str(file_info.get("name", "内六角杯头螺丝"))

    # 优先用文件名里的螺纹规格，缺省再用 PDF 里的
    major_d = float(file_info.get("major_d", pdf_dims.get("major_d", 5.0)))
    pitch = float(file_info.get("pitch", pdf_dims.get("pitch", default_pitch(major_d))))
    length = float(file_info.get("length", pdf_dims.get("length", 12.0)))

    # 识别类型（优先文件名，其次 PDF 文本）
    head_type = file_info.get("head_type") or _detect_head_type_pdf(text)
    drive_type = file_info.get("drive_type") or _detect_drive_type_pdf(text)
    tail_type = file_info.get("tail_type") or _detect_tail_type_pdf(text)

    # 用对应标准表补全头部尺寸
    iso = lookup_iso(major_d, head_type)

    head_d = pdf_dims.get("head_d", iso["head_d"])
    head_h = pdf_dims.get("head_h", iso["head_h"])
    hex_size = iso.get("hex", 4.0)
    socket_depth = iso.get("socket_depth", 2.5)

    # 十字槽号
    cross_drive_size = get_cross_drive_size(major_d)

    return ScrewParams(
        part_no=part_no,
        name=name,
        major_d=major_d,
        pitch=pitch,
        length=length,
        head_d=head_d,
        head_h=head_h,
        drive_type=drive_type,
        head_type=head_type,
        tail_type=tail_type,
        hex_size=hex_size,
        socket_depth=socket_depth,
        cross_drive_size=cross_drive_size,
        gb_standard=lookup_gb_standard(head_type, drive_type, tail_type),
    )
