# -*- coding: utf-8 -*-
"""几何生成器单元测试."""

import sys
from pathlib import Path

# 让测试在没有安装包或 PYTHONPATH 的情况下也能找到源码
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest

from standard_parts_ai.generators import build_screw
from standard_parts_ai.models import ScrewParams
from standard_parts_ai.standards import get_cross_drive_size, lookup_iso


class TestGeneratorGeometry(unittest.TestCase):
    """测试螺丝几何生成的正确性."""

    @staticmethod
    def _make_params(major_d: float, pitch: float, length: float, head_type: str) -> ScrewParams:
        iso = lookup_iso(major_d, head_type)
        return ScrewParams(
            part_no=f"M{major_d}x{length}_{head_type}",
            name="test",
            major_d=major_d,
            pitch=pitch,
            length=length,
            head_d=iso["head_d"],
            head_h=iso["head_h"],
            drive_type="hex" if head_type == "socket" else "cross",
            head_type=head_type,
            tail_type="flat",
            hex_size=iso.get("hex", 4.0),
            socket_depth=iso.get("socket_depth", 2.5),
            cross_drive_size=get_cross_drive_size(major_d),
        )

    def _assert_single_solid(self, params: ScrewParams) -> None:
        screw = build_screw(params)
        self.assertEqual(len(screw.val().Solids()), 1, "螺丝应该是一个整体 Solid")

    def _assert_height(self, params: ScrewParams, expected: float) -> None:
        screw = build_screw(params)
        b = screw.val().BoundingBox()
        self.assertAlmostEqual(b.zmax, expected, delta=0.2)
        self.assertAlmostEqual(b.zmin, 0.0, delta=0.05)

    def test_head_heights_m5(self):
        """M5 各头型的总高度应为 length + head_h."""
        for head_type in ("socket", "pan", "round", "countersunk"):
            with self.subTest(head_type=head_type):
                params = self._make_params(5.0, 0.8, 12.0, head_type)
                self._assert_height(params, 12.0 + params.head_h)

    def test_extreme_sizes(self):
        """M1.4 小规格和 M8 大规格都应生成有效 Solid."""
        for major, pitch, length in ((1.4, 0.3, 5.0), (8.0, 1.25, 20.0)):
            for head_type in ("socket", "pan", "round", "countersunk"):
                with self.subTest(major=major, head_type=head_type):
                    params = self._make_params(major, pitch, length, head_type)
                    self._assert_single_solid(params)

    def test_sharp_tail_extends_below(self):
        """尖尾螺丝的 z 最小值应小于 0."""
        params = self._make_params(5.0, 0.8, 12.0, "socket")
        params.tail_type = "sharp"
        screw = build_screw(params)
        b = screw.val().BoundingBox()
        self.assertLess(b.zmin, -0.1)
        self.assertEqual(len(screw.val().Solids()), 1)


if __name__ == "__main__":
    unittest.main()
