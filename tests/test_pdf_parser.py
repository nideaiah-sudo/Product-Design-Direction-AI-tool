# -*- coding: utf-8 -*-
"""PDF 解析模块单元测试."""

import sys
from pathlib import Path

# 让测试在没有安装包或 PYTHONPATH 的情况下也能找到源码
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest

from standard_parts_ai.pdf_parser import _parse_dimension_line_pdf, _parse_filename


class TestPdfParser(unittest.TestCase):
    """PDF 解析测试."""

    def test_parse_filename_m5x12(self):
        """测试从文件名解析 M5x12 规格."""
        path = Path("326010708_Screw;内六角杯头螺丝-304不锈钢-M5x12mm_表面钝化.pdf")
        info = _parse_filename(path)
        self.assertEqual(info["part_no"], "326010708")
        self.assertEqual(info["name"], "内六角杯头螺丝")
        self.assertEqual(info["major_d"], 5.0)
        self.assertEqual(info["length"], 12.0)
        self.assertEqual(info["pitch"], 0.8)
        self.assertEqual(info["head_type"], "socket")
        self.assertEqual(info["drive_type"], "hex")
        self.assertEqual(info["tail_type"], "flat")

    def test_parse_filename_cross_pan(self):
        """测试从文件名解析十字盘头螺丝."""
        path = Path("123456_Screw;十字盘头螺丝-M3x8mm.pdf")
        info = _parse_filename(path)
        self.assertEqual(info["head_type"], "pan")
        self.assertEqual(info["drive_type"], "cross")

    def test_parse_filename_pb2x6_round(self):
        """测试从文件名解析自攻螺丝 PB2x6mm."""
        path = Path(
            "3260000034_Screw;十字圆头平尾自攻牙螺丝,PB2x6mm,碳钢,镀镍,银色,盐雾48H(十字槽PH1).pdf"
        )
        info = _parse_filename(path)
        self.assertEqual(info["part_no"], "3260000034")
        self.assertEqual(info["name"], "十字圆头平尾自攻牙螺丝")
        self.assertEqual(info["major_d"], 2.0)
        self.assertEqual(info["length"], 6.0)
        self.assertEqual(info["pitch"], 0.4)
        self.assertEqual(info["head_type"], "round")
        self.assertEqual(info["drive_type"], "cross")
        self.assertEqual(info["tail_type"], "flat")

    def test_parse_dimension_line_m5x12(self):
        """测试从 PDF 文本解析螺纹和长度."""
        text = "M5X0.8-6g 12.0±0.35 ∅8.28-∅8.72 4.82-5.00"
        dims = _parse_dimension_line_pdf(text)
        self.assertEqual(dims["major_d"], 5.0)
        self.assertEqual(dims["pitch"], 0.8)
        self.assertEqual(dims["length"], 12.0)
        self.assertEqual(dims["head_d"], 8.5)
        self.assertEqual(dims["head_h"], 4.91)

    def test_parse_dimension_line_drawing_tolerance(self):
        """测试工程图常见公差格式：10.0+0/-0.5、∅5.5+0.5、2.0±0.15."""
        text = "M3X0.5-6g 2.0±0.15 ∅5.5+0.5 10.0+0/-0.5"
        dims = _parse_dimension_line_pdf(text)
        self.assertEqual(dims["major_d"], 3.0)
        self.assertEqual(dims["pitch"], 0.5)
        self.assertEqual(dims["length"], 10.0)
        self.assertEqual(dims["head_d"], 5.5)
        self.assertEqual(dims["head_h"], 2.0)

    def test_parse_dimension_line_m5x12_without_mm(self):
        """测试 M5x12 不会把 12 误判为螺距."""
        text = "M5x12-6g 12.0±0.35 ∅8.28-∅8.72 4.82-5.00"
        dims = _parse_dimension_line_pdf(text)
        self.assertEqual(dims["major_d"], 5.0)
        self.assertEqual(dims["length"], 12.0)
        self.assertEqual(dims["pitch"], 0.8)

    def test_parse_dimension_line_three_part(self):
        """测试三段式 M5x0.8x12."""
        text = "M5x0.8x12 头径 8.5 头高 5.0"
        dims = _parse_dimension_line_pdf(text)
        self.assertEqual(dims["major_d"], 5.0)
        self.assertEqual(dims["pitch"], 0.8)
        self.assertEqual(dims["length"], 12.0)
        self.assertEqual(dims["head_d"], 8.5)
        self.assertEqual(dims["head_h"], 5.0)

    def test_parse_dimension_line_keywords(self):
        """测试中文关键字解析."""
        text = "螺纹规格 M5x0.8 长度 12 头径 8.5 头高 5.0"
        dims = _parse_dimension_line_pdf(text)
        self.assertEqual(dims["major_d"], 5.0)
        self.assertEqual(dims["pitch"], 0.8)
        self.assertEqual(dims["length"], 12.0)
        self.assertEqual(dims["head_d"], 8.5)
        self.assertEqual(dims["head_h"], 5.0)

    def test_parse_dimension_line_small_screw(self):
        """测试小规格螺丝 M1.4x0.3."""
        text = "M1.4x0.3-6g 5.0±0.1 ∅2.6-∅2.8 1.3-1.5"
        dims = _parse_dimension_line_pdf(text)
        self.assertEqual(dims["major_d"], 1.4)
        self.assertEqual(dims["pitch"], 0.3)
        self.assertEqual(dims["length"], 5.0)
        self.assertEqual(dims["head_d"], 2.7)
        self.assertEqual(dims["head_h"], 1.4)

    def test_parse_filename_m5x0_8x12(self):
        """测试三段式文件名 M5x0.8x12."""
        path = Path("M5x0.8x12.pdf")
        info = _parse_filename(path)
        self.assertEqual(info["major_d"], 5.0)
        self.assertEqual(info["pitch"], 0.8)
        self.assertEqual(info["length"], 12.0)

    def test_parse_filename_without_mm(self):
        """测试没有 mm 后缀的文件名."""
        path = Path("M1.4x5.pdf")
        info = _parse_filename(path)
        self.assertEqual(info["major_d"], 1.4)
        self.assertEqual(info["length"], 5.0)
        self.assertEqual(info["pitch"], 0.3)


if __name__ == "__main__":
    unittest.main()
