# -*- coding: utf-8 -*-
"""OCR 图片解析模块：从螺丝照片中提取参数（照片专用路径）."""

from __future__ import annotations

import re
from pathlib import Path

from ._tesseract import get_tesseract_cmd
from ._text_utils import normalize_text
from .models import ScrewParams
from .standards import (
    HEAD_TYPE_MAP,
    DRIVE_TYPE_MAP,
    TAIL_TYPE_MAP,
    default_pitch,
    get_cross_drive_size,
    lookup_gb_standard,
    lookup_iso,
)


try:
    import pytesseract
    from PIL import Image, ImageOps, ImageFilter
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    ImageFilter = None  # type: ignore[assignment]


def extract_text_from_image(image_path: Path) -> str:
    """使用 Tesseract OCR 从图片中提取文本（照片专用）.

    包含图像预处理：灰度化、放大、对比度增强、去噪、自适应二值化，
    分别用中文+英文、英文多种 PSM 模式识别，合并结果提高召回率。
    同时尝试 0°/90°/180°/270° 旋转，以识别旋转 90° 的文字。
    """
    if pytesseract is None or Image is None or ImageOps is None or ImageFilter is None:
        raise RuntimeError("请先安装依赖: pip install pytesseract pillow")

    pytesseract.pytesseract.tesseract_cmd = get_tesseract_cmd()

    with Image.open(image_path) as original:
        texts: list[str] = []
        angles = [0]
        first_pass = _ocr_rotated(original, 0)
        texts.append(first_pass)

        # 如果正着 OCR 没有识别到 M<大径> 或 mm 单位，再尝试其他旋转角度
        if not re.search(r"M\s*\d|mm|\d+\s*mm", first_pass, re.IGNORECASE):
            for angle in (90, 180, 270):
                texts.append(_ocr_rotated(original, angle))

    return "\n".join(texts)


def _ocr_rotated(original: Image.Image, angle: int) -> str:
    """对图片按指定角度旋转后进行 OCR，返回识别文本."""
    if angle != 0:
        image = original.rotate(angle, expand=True)
    else:
        image = original

    # 1. 转为灰度
    image = image.convert("L")

    # 2. 智能缩放：小图放大、大图保持原样
    width, height = image.size
    min_side = min(width, height)
    if min_side < 800:
        scale = 800.0 / min_side
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size, Image.LANCZOS)

    # 3. 轻度去噪
    image = image.filter(ImageFilter.MedianFilter(size=3))

    # 4. 自动对比度 + 反色处理，确保黑字白底
    image = ImageOps.autocontrast(image)
    mean_pixel = sum(image.getdata()) / (image.width * image.height)
    if mean_pixel > 128:
        # 图像是亮底暗字（文本是白色），需要反色成黑字白底
        image = ImageOps.invert(image)

    # 5. OCR：用多种 PSM 配置识别，合并结果
    texts: list[str] = []

    # 5.1 中文+英文，自动布局（适合读取中文标签和大字规格）
    try:
        text1 = pytesseract.image_to_string(image, lang="chi_sim+eng", config="--psm 6")
        texts.append(text1)
    except pytesseract.pytesseract.TesseractError:
        pass

    # 5.2 英文+数字白名单，单行/单字/稀疏模式（适合读取规格 M4*6 / 7.2mm）
    whitelist = "MmXxXx×*0123456789.mm "
    for psm in ("6", "7", "11", "3"):
        try:
            custom_config = f"--psm {psm} -c tessedit_char_whitelist={whitelist}"
            text = pytesseract.image_to_string(image, lang="eng", config=custom_config)
            texts.append(text)
        except pytesseract.pytesseract.TesseractError:
            continue

    return "\n".join(texts)


def _normalize_major_d(major_d: float) -> float:
    """把 OCR 识别出的非标准螺纹大径修正为最接近的标准值."""
    standard_values = [1.2, 1.4, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
    return min(standard_values, key=lambda x: abs(x - major_d))


def _preprocess_ocr_text(text: str) -> str:
    """对 OCR 原始文本做清洗，修复常见噪声."""
    # 将全角、特殊分隔符统一（* 也会变成 x）
    text = normalize_text(text)
    # 合并连续空白
    text = re.sub(r"\s+", " ", text)
    # 修复 "0 . 5" / "0. 5" / "0 .5" 等数字内部空格
    text = re.sub(r"(\d)\s*\.\s*(\d)", r"\1.\2", text)
    # 修复 "M 5 x 12" -> "M5x12"
    text = re.sub(r"M\s+(\d+(?:\.\d+)?)", r"M\1", text, flags=re.IGNORECASE)
    # 修复 "3 x 12" / "3 * 12" -> "3x12"
    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)",
        r"\1x\2",
        text,
    )
    # 常见 OCR 错误：O -> 0
    text = re.sub(r"(?<![A-Za-z])O(?=\d)", "0", text)
    return text


def _major_from_pitch(pitch: float) -> float | None:
    """根据标准粗牙螺距反推螺纹大径."""
    coarse = {
        0.3: 1.4,
        0.4: 2.0,
        0.45: 2.5,
        0.5: 3.0,
        0.7: 4.0,
        0.8: 5.0,
        1.0: 6.0,
        1.25: 8.0,
        1.5: 10.0,
    }
    return coarse.get(round(pitch, 2))


def _select_best_major(major_candidates: list[float], result: dict[str, float], all_mm: list[float]) -> float:
    """从多个 M 候选中，根据 mm 值和螺距选出最可能的大径."""
    if len(major_candidates) == 1:
        return major_candidates[0]

    common_lengths = {
        3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28,
        30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100,
    }
    best: float | None = None
    best_score = -1

    for major in major_candidates:
        score = 0
        # 存在合理长度值
        if any(major < v <= major * 25 and round(v, 1) in common_lengths for v in all_mm):
            score += 2
        # 存在合理头径
        if any(major * 1.2 <= v <= major * 5.0 for v in all_mm):
            score += 2
        # 螺距一致性
        if "pitch" in result:
            if abs(default_pitch(major) - result["pitch"]) < 0.05:
                score += 3
        # 头高一致性
        if "head_h" in result:
            if abs(result["head_h"] - major) <= 2.0:
                score += 1
        if score > best_score:
            best_score = score
            best = major

    if best is None:
        # 没有可用线索时，取最小候选（通常 OCR 噪声为大值）
        best = min(major_candidates)
    return best


def _detect_head_type_image(text: str) -> str:
    """从照片 OCR 文本中识别螺丝头型."""
    lower = text.lower()
    for keyword, head_type in HEAD_TYPE_MAP.items():
        if keyword in lower:
            return head_type
    return "socket"


def _detect_drive_type_image(text: str) -> str:
    """从照片 OCR 文本中识别驱动类型."""
    lower = text.lower()
    for keyword, drive_type in DRIVE_TYPE_MAP.items():
        if keyword in lower:
            return drive_type
    return "hex"


def _detect_tail_type_image(text: str) -> str:
    """从照片 OCR 文本中识别尾部类型."""
    lower = text.lower()
    for keyword, tail_type in TAIL_TYPE_MAP.items():
        if keyword in lower:
            return tail_type
    return "flat"


def _parse_dimension_line_image(text: str) -> dict[str, float]:
    """从照片 OCR 文本解析关键尺寸（照片专用）."""
    result: dict[str, float] = {}
    text = _preprocess_ocr_text(text)

    # 收集所有 M<major> 候选，后面再根据尺寸推断最可能的大径。
    major_candidates: list[float] = []
    for m in re.finditer(
        r"(?<![A-Za-z0-9])M\s*([1-9]\d*(?:\.\d+)?)(?:\s*[xX]\s*(\d+(?:\.\d+)?))?(?:\s*[xX]\s*(\d+(?:\.\d+)?))?",
        text,
        re.IGNORECASE,
    ):
        major_val = float(m.group(1))
        # 归一化到标准大径
        major_val = _normalize_major_d(major_val)
        if major_val not in major_candidates:
            major_candidates.append(major_val)
        # 顺手从规格里提取长度/螺距，但不立即确定 major
        values = [float(g) for g in (m.group(2), m.group(3)) if g is not None]
        if values:
            if len(values) == 1:
                if values[0] <= 2.0 and "pitch" not in result:
                    result["pitch"] = values[0]
                elif "length" not in result:
                    result["length"] = values[0]
            else:
                if "pitch" not in result:
                    result["pitch"] = values[0]
                if "length" not in result:
                    result["length"] = values[1]

    # 图片中常见 "3*10" 省略 M 的情况，补充识别为 M3x10。
    # 同时收集候选大径。
    for spec_match in re.finditer(
        r"(?<![A-Za-z])(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)",
        text,
    ):
        major_candidate = float(spec_match.group(1))
        length_candidate = float(spec_match.group(2))
        if major_candidate not in (1.2, 1.4, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0):
            continue
        if length_candidate <= 2.0:
            continue
        if major_candidate not in major_candidates:
            major_candidates.append(major_candidate)
        # 用该规格补全长
        if "length" not in result:
            result["length"] = length_candidate
        break

    # 中文标签补充
    pitch_match = re.search(r"牙距[：:]?\s*(\d+(?:\.\d+)?)", text)
    if pitch_match:
        result["pitch"] = float(pitch_match.group(1))

    length_match = re.search(r"(?:螺纹长度|螺杆长度|长度|总长)[：:]?\s*(\d+(?:\.\d+)?)", text)
    if length_match:
        result["length"] = float(length_match.group(1))

    head_h_match = re.search(r"(?:头部厚度|头高|头部高度)[：:]?\s*(\d+(?:\.\d+)?)", text)
    if head_h_match:
        result["head_h"] = float(head_h_match.group(1))

    head_d_match = re.search(r"(?:头部直径|头径)[：:]?\s*(\d+(?:\.\d+)?)", text)
    if head_d_match:
        result["head_d"] = float(head_d_match.group(1))

    hex_match = re.search(r"(?:六角对边|对边)[：:]?\s*(\d+(?:\.\d+)?)", text)
    if hex_match:
        result["hex_size"] = float(hex_match.group(1))

    # 兜底：从 "数字mm" 中补头径/头高（仅在未识别到时，且结果需合理）
    all_mm = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*mm", text, re.IGNORECASE)]
    major_d = result.get("major_d", 0.0)

    # 螺距兜底：没有明确牙距时，从 mm 值里找标准螺距。
    if "pitch" not in result and all_mm:
        standard_pitches = {0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.75, 0.8, 1.0, 1.25, 1.5}
        if major_d > 0:
            candidates = [v for v in all_mm if v < major_d / 1.5 and round(v, 2) in standard_pitches]
        else:
            # 大径还没识别出来时，先取一个标准螺距候选，后续再用它反推大径
            candidates = [v for v in all_mm if round(v, 2) in standard_pitches]
        if candidates:
            result["pitch"] = min(candidates)
            major_d = result.get("major_d", 0.0)

    # 螺距与大径一致性校验：
    # OCR 可能把 "M3*10" 读成 "M04" 或读丢 M，但牙距 0.5mm 明确对应 M3。
    if "pitch" in result:
        inferred_major = _major_from_pitch(result["pitch"])
        if inferred_major is not None:
            current_major = result.get("major_d")
            if current_major is None or abs(default_pitch(current_major) - result["pitch"]) > 0.05:
                result["major_d"] = inferred_major
                major_d = inferred_major

    # 如果 OCR 出现多个 M 候选（如 M5、M12、M1.2），根据尺寸推断最合理的大径。
    if major_candidates:
        result["major_d"] = _select_best_major(major_candidates, result, all_mm)
        major_d = result["major_d"]

    if "head_h" not in result and all_mm:
        # 头高通常在 1.0 ~ 大径+2 之间，应明显大于螺距
        pitch = result.get("pitch", 0.0)
        head_d = result.get("head_d", float("inf"))
        candidates = [
            v
            for v in all_mm
            if 1.0 <= v <= major_d + 2.0 and v > pitch + 0.2 and v < head_d
        ]
        if candidates:
            # 默认按内六角（socket）处理时，头高通常接近螺纹大径；
            # 其他头型通常头高较小，取最小值。
            if _detect_head_type_image(text) == "socket":
                result["head_h"] = min(candidates, key=lambda v: abs(v - major_d))
            else:
                result["head_h"] = min(candidates)

    if "head_d" not in result and all_mm:
        # 头径通常是大径的 1.2~5 倍，且不等于已识别的长度，
        # 同时应排除标准长度值，避免把螺杆长度误当头部直径。
        common_lengths = {
            3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28,
            30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100,
        }
        length = result.get("length")
        candidates = [
            v
            for v in all_mm
            if major_d * 1.2 <= v <= major_d * 5.0 and v != length and round(v, 1) not in common_lengths
        ]
        if candidates:
            result["head_d"] = max(candidates)

    # 兜底长度：如果仍没识别出长度，从 mm 值里挑一个合理的标准长度。
    # 例如图里标题没被识别，但 "6mm" 真实存在，且 33mm 是 OCR 噪声时。
    if "length" not in result and all_mm and major_d > 0:
        used = {
            result.get("head_d"),
            result.get("head_h"),
            result.get("hex_size"),
            result.get("pitch"),
        }
        common_lengths = {
            3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28,
            30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100,
        }
        candidates = [
            v
            for v in all_mm
            if major_d < v <= major_d * 25 and v not in used and round(v, 1) in common_lengths
        ]
        if candidates:
            # 取最小且合理的标准长度
            result["length"] = min(candidates)

    # 长度校验：OCR 常把标题 "M4*6" 误读成 "M4*33"，
    # 如果当前长度在 "数字mm" 中找不到佐证，但另一个规格候选长度有，则修正。
    if "length" in result and all_mm and "major_d" in result:
        current_len = result["length"]
        major_d = result["major_d"]

        # 收集所有可能的规格长度候选
        spec_len_candidates: list[float] = []
        for m4 in re.finditer(
            r"(?<![A-Za-z0-9])M\s*([1-9]\d*(?:\.\d+)?)(?:\s*[xX]\s*(\d+(?:\.\d+)?))?(?:\s*[xX]\s*(\d+(?:\.\d+)?))?",
            text,
            re.IGNORECASE,
        ):
            vals = [float(g) for g in (m4.group(2), m4.group(3)) if g is not None]
            for v in vals:
                if v > 2.0:
                    spec_len_candidates.append(v)
        for m_no in re.finditer(
            r"(?<![A-Za-z])(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)",
            text,
        ):
            if float(m_no.group(1)) == major_d:
                spec_len_candidates.append(float(m_no.group(2)))

        if current_len not in all_mm:
            # 优先选择同时在 mm 值里出现的规格长度
            for cand in spec_len_candidates:
                if cand in all_mm and major_d < cand <= major_d * 50:
                    result["length"] = cand
                    break
            else:
                # 否则看看 mm 值里是否有更"标准"的整数长度
                # （OCR 可能把 6 错读成 33，而 33 不是常见长度）
                common_lengths = {
                    3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28,
                    30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 90, 100,
                }
                for v in sorted(all_mm):
                    if (
                        major_d < v <= major_d * 25
                        and round(v, 1) in common_lengths
                    ):
                        result["length"] = v
                        break

    # 最终螺距-大径一致性修正：
    # 若兜底得到的螺距与标准粗牙螺距不符，按标准粗牙修正。
    if "major_d" in result and "pitch" in result:
        major_d = result["major_d"]
        if abs(default_pitch(major_d) - result["pitch"]) > 0.05:
            result["pitch"] = default_pitch(major_d)

    return result


def _parse_spec_from_text(text: str) -> dict[str, float | str]:
    """从照片 OCR 文本中解析螺丝参数."""
    result: dict[str, float | str] = {}

    # 1. 尺寸解析
    dims = _parse_dimension_line_image(text)
    for key in ("major_d", "pitch", "length", "head_d", "head_h", "hex_size"):
        if key in dims:
            result[key] = dims[key]

    # 2. 类型识别（照片专用）
    result["head_type"] = _detect_head_type_image(text)
    result["drive_type"] = _detect_drive_type_image(text)
    result["tail_type"] = _detect_tail_type_image(text)

    return result


def parse_image(image_path: Path) -> ScrewParams:
    """从螺丝图片解析参数并构造 ScrewParams（照片专用入口）."""
    text = extract_text_from_image(image_path)
    dims = _parse_spec_from_text(text)

    major_d = float(dims.get("major_d", 5.0))
    length = float(dims.get("length", 12.0))
    pitch = float(dims.get("pitch", default_pitch(major_d)))
    head_type = str(dims.get("head_type", "socket"))
    drive_type = str(dims.get("drive_type", "hex"))
    tail_type = str(dims.get("tail_type", "flat"))

    # OCR 容错：把螺纹大径修正到最接近的标准值
    major_d = _normalize_major_d(major_d)

    iso = lookup_iso(major_d, head_type)

    head_d = float(dims.get("head_d", iso["head_d"]))
    head_h = float(dims.get("head_h", iso["head_h"]))
    hex_size = float(dims.get("hex_size", iso.get("hex", 4.0)))
    socket_depth = iso.get("socket_depth", 2.5)

    _major_str = str(int(major_d)) if major_d == int(major_d) else str(major_d)
    _length_str = str(int(length)) if length == int(length) else str(length)

    return ScrewParams(
        part_no=f"M{_major_str}x{_length_str}",
        name="螺丝",
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
        cross_drive_size=get_cross_drive_size(major_d),
        gb_standard=lookup_gb_standard(head_type, drive_type, tail_type),
    )
