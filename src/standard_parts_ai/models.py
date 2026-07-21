# -*- coding: utf-8 -*-
"""螺丝参数数据模型."""

from dataclasses import dataclass


@dataclass
class ScrewParams:
    """螺丝参数容器"""

    part_no: str
    name: str
    major_d: float
    pitch: float
    length: float
    head_d: float
    head_h: float
    drive_type: str  # "hex", "cross"
    head_type: str  # "socket", "pan", "round", "countersunk"
    tail_type: str  # "flat", "sharp"
    hex_size: float  # 仅内六角有效
    socket_depth: float  # 仅内六角有效
    cross_drive_size: str  # 十字槽号
    gb_standard: str = ""  # 对应国标序列号

    @property
    def minor_d(self) -> float:
        """ISO 小径计算"""
        return self.major_d - 1.0825 * self.pitch

    @property
    def thread_h(self) -> float:
        return (self.major_d - self.minor_d) / 2

    def __str__(self) -> str:  # noqa: D105
        # 类型中文映射（仅用于显示）
        HEAD_TYPE_CN = {
            "socket": "内六角杯头",
            "pan": "盘头",
            "round": "圆头",
            "countersunk": "沉头",
        }
        DRIVE_TYPE_CN = {
            "hex": "内六角",
            "cross": "十字",
        }
        TAIL_TYPE_CN = {
            "flat": "平尾",
            "sharp": "尖尾",
        }
        head_cn = HEAD_TYPE_CN.get(self.head_type, self.head_type)
        drive_cn = DRIVE_TYPE_CN.get(self.drive_type, self.drive_type)
        tail_cn = TAIL_TYPE_CN.get(self.tail_type, self.tail_type)

        gb = f"  国标: {self.gb_standard}\n" if self.gb_standard else ""
        return (
            f"{self.part_no} {self.name}\n"
            f"  螺纹: M{self.major_d:.1f} x {self.pitch:.2f} - 6g\n"
            f"  长度: {self.length:.2f} mm\n"
            f"  外径: {self.major_d:.3f} mm\n"
            f"  内径: {self.minor_d:.3f} mm (底孔)\n"
            f"  头部: d={self.head_d:.2f} x h={self.head_h:.2f} mm ({head_cn})\n"
            f"  驱动: {drive_cn}\n"
            f"  尾部: {tail_cn}\n"
            f"{gb}"
        )
