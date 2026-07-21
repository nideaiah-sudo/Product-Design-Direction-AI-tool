# -*- coding: utf-8 -*-
"""ISO / DIN 标准尺寸表."""

# ISO 4762 / DIN 912 内六角杯头螺丝标准尺寸表（单位 mm）
ISO_TABLE: dict[str, dict[str, float]] = {
    "M1.2": {"head_d": 2.30, "head_h": 1.20, "hex": 1.00, "socket_depth": 0.60},
    "M1.4": {"head_d": 2.60, "head_h": 1.40, "hex": 1.30, "socket_depth": 0.80},
    "M2": {"head_d": 3.50, "head_h": 2.00, "hex": 1.50, "socket_depth": 1.00},
    "M2.5": {"head_d": 4.50, "head_h": 2.50, "hex": 2.00, "socket_depth": 1.20},
    "M3": {"head_d": 5.50, "head_h": 3.00, "hex": 2.50, "socket_depth": 1.50},
    "M4": {"head_d": 7.00, "head_h": 4.00, "hex": 3.00, "socket_depth": 2.00},
    "M5": {"head_d": 8.50, "head_h": 5.00, "hex": 4.00, "socket_depth": 2.50},
    "M6": {"head_d": 10.0, "head_h": 6.00, "hex": 5.00, "socket_depth": 3.00},
    "M8": {"head_d": 13.0, "head_h": 8.00, "hex": 6.00, "socket_depth": 4.00},
    "M10": {"head_d": 16.0, "head_h": 10.0, "hex": 8.00, "socket_depth": 5.00},
}

# 盘头螺丝（Pan Head，ISO 7045 / DIN 7985）近似标准尺寸
# 注：M3 取 head_d=5.5, head_h=2.0，以匹配常见规格书图纸（∅5.5×2.0）
PAN_HEAD_TABLE: dict[str, dict[str, float]] = {
    "M1.4": {"head_d": 2.8, "head_h": 0.9},
    "M1.6": {"head_d": 3.2, "head_h": 1.1},
    "M2": {"head_d": 3.8, "head_h": 1.3},
    "M2.5": {"head_d": 4.7, "head_h": 1.6},
    "M3": {"head_d": 5.5, "head_h": 2.0},
    "M4": {"head_d": 7.5, "head_h": 2.5},
    "M5": {"head_d": 9.2, "head_h": 3.1},
    "M6": {"head_d": 11.0, "head_h": 3.7},
    "M8": {"head_d": 14.5, "head_h": 4.9},
}

# 圆头螺丝（Round / Button Head，ISO 7380）近似标准尺寸
ROUND_HEAD_TABLE: dict[str, dict[str, float]] = {
    "M1.4": {"head_d": 3.0, "head_h": 1.0},
    "M1.6": {"head_d": 3.5, "head_h": 1.2},
    "M2": {"head_d": 4.0, "head_h": 1.3},
    "M2.5": {"head_d": 5.0, "head_h": 1.6},
    "M3": {"head_d": 6.0, "head_h": 1.9},
    "M4": {"head_d": 8.0, "head_h": 2.5},
    "M5": {"head_d": 10.0, "head_h": 3.1},
    "M6": {"head_d": 12.0, "head_h": 3.7},
    "M8": {"head_d": 16.0, "head_h": 4.9},
}

# 沉头螺丝（Countersunk Head，ISO 7997 / DIN 965）近似标准尺寸
COUNTERSUNK_HEAD_TABLE: dict[str, dict[str, float]] = {
    "M1.4": {"head_d": 2.8, "head_h": 0.8},
    "M1.6": {"head_d": 3.2, "head_h": 1.0},
    "M2": {"head_d": 4.0, "head_h": 1.2},
    "M2.5": {"head_d": 5.0, "head_h": 1.5},
    "M3": {"head_d": 6.0, "head_h": 1.7},
    "M4": {"head_d": 8.0, "head_h": 2.3},
    "M5": {"head_d": 10.0, "head_h": 2.8},
    "M6": {"head_d": 12.0, "head_h": 3.3},
    "M8": {"head_d": 16.0, "head_h": 4.3},
}

# 十字槽国标 GB/T 尺寸（单位 mm）
CROSS_DRIVE_TABLE: dict[str, dict[str, float]] = {
    "0": {"m": 0.45, "width": 0.30, "depth": 0.45},
    "1": {"m": 0.65, "width": 0.40, "depth": 0.60},
    "2": {"m": 0.95, "width": 0.60, "depth": 0.85},
    "3": {"m": 1.40, "width": 0.90, "depth": 1.20},
    "4": {"m": 2.30, "width": 1.50, "depth": 1.80},
}

# 国标 GB/T 对应表（头型 + 驱动 + 尾部）
# 注：尾部 flat/sharp 不影响标准号主体，self-tapping 对应 GB/T 845/846/847
GB_STANDARD_MAP: dict[tuple[str, str, str], str] = {
    # 内六角
    ("socket", "hex", "flat"): "GB/T 70.1-2008",
    ("socket", "hex", "sharp"): "GB/T 70.1-2008",
    # 十字盘头
    ("pan", "cross", "flat"): "GB/T 818-2016",
    ("pan", "cross", "sharp"): "GB/T 845-2017",
    # 十字圆头
    ("round", "cross", "flat"): "GB/T 67-2016",
    ("round", "cross", "sharp"): "GB/T 847-2017",
    # 十字沉头
    ("countersunk", "cross", "flat"): "GB/T 819-2016",
    ("countersunk", "cross", "sharp"): "GB/T 846-2017",
}


def lookup_gb_standard(head_type: str, drive_type: str, tail_type: str) -> str:
    """根据头型/驱动/尾部查找对应国标号，找不到返回“非国标”."""
    return GB_STANDARD_MAP.get((head_type, drive_type, tail_type), "非国标")


HEAD_TYPE_MAP: dict[str, str] = {
    "杯头": "socket",
    "圆柱头": "socket",
    "内六角": "socket",
    "平头": "socket",
    "盘头": "pan",
    "圆头": "round",
    "沉头": "countersunk",
    "倒边": "countersunk",
}

DRIVE_TYPE_MAP: dict[str, str] = {
    "内六角": "hex",
    "十字": "cross",
}

TAIL_TYPE_MAP: dict[str, str] = {
    "平尾": "flat",
    "尖尾": "sharp",
}


def default_pitch(major_d: float) -> float:
    """返回标准粗牙螺距."""
    coarse = {1.2: 0.25, 1.4: 0.3, 2: 0.4, 2.5: 0.45, 3: 0.5, 4: 0.7, 5: 0.8, 6: 1.0, 8: 1.25, 10: 1.5}
    return coarse.get(round(major_d, 1), 1.0)


def get_cross_drive_size(major_d: float) -> str:
    """根据螺纹大径自动选择十字槽号."""
    if major_d <= 1.4:
        return "0"
    if major_d <= 2.0:
        return "1"
    if major_d <= 3.0:
        return "2"
    if major_d <= 5.0:
        return "3"
    return "4"


def _size_key(major_d: float) -> str:
    """根据螺纹大径生成标准表键名."""
    # 常见规格：M1.2, M1.4, M2, M2.5, M3, ...
    if abs(major_d - 1.2) < 0.05:
        return "M1.2"
    if abs(major_d - 1.4) < 0.05:
        return "M1.4"
    if abs(major_d - 2.5) < 0.05:
        return "M2.5"
    return f"M{int(round(major_d))}"


def get_head_table(head_type: str):
    """根据头型返回对应的标准尺寸表."""
    tables = {
        "socket": ISO_TABLE,
        "pan": PAN_HEAD_TABLE,
        "round": ROUND_HEAD_TABLE,
        "countersunk": COUNTERSUNK_HEAD_TABLE,
    }
    return tables.get(head_type, ISO_TABLE)


def lookup_iso(major_d: float, head_type: str = "socket") -> dict[str, float]:
    """根据螺纹大径和头型查找标准尺寸，支持缺省回退."""
    table = get_head_table(head_type)
    size_key = _size_key(major_d)
    return table.get(size_key, ISO_TABLE["M5"])
