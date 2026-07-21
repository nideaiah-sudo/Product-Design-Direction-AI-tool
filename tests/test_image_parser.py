# -*- coding: utf-8 -*-
"""图片 OCR 解析模块单元测试."""

import sys
from pathlib import Path

# 让测试在没有安装包或 PYTHONPATH 的情况下也能找到源码
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from unittest.mock import patch

from standard_parts_ai.image_parser import (
    _detect_drive_type_image,
    _detect_head_type_image,
    _detect_tail_type_image,
    _normalize_major_d,
    _parse_dimension_line_image,
    _parse_spec_from_text,
    _preprocess_ocr_text,
)


class TestImageParser(unittest.TestCase):
    """照片 OCR 解析测试."""

    def test_normalize_major_d(self):
        """测试螺纹大径归一化."""
        self.assertEqual(_normalize_major_d(5.1), 5.0)
        self.assertEqual(_normalize_major_d(1.45), 1.4)
        self.assertEqual(_normalize_major_d(9.9), 10.0)

    def test_preprocess_ocr_text(self):
        """测试 OCR 文本清洗."""
        text = "M 5 x 12 牙距 0.8"
        cleaned = _preprocess_ocr_text(text)
        self.assertIn("M5x12", cleaned)
        self.assertIn("牙距 0.8", cleaned)

    def test_parse_dimension_line_image(self):
        """测试照片 OCR 尺寸解析."""
        text = "M3x8 牙距0.5 长度8 头径6.0 头高2.1"
        dims = _parse_dimension_line_image(text)
        self.assertEqual(dims["major_d"], 3.0)
        self.assertEqual(dims["length"], 8.0)
        self.assertEqual(dims["pitch"], 0.5)
        self.assertEqual(dims["head_d"], 6.0)
        self.assertEqual(dims["head_h"], 2.1)

    def test_parse_dimension_line_image_with_noise(self):
        """测试带噪声的 OCR 尺寸解析."""
        text = "M 3 x 8 牙距 0.5"
        dims = _parse_dimension_line_image(text)
        self.assertEqual(dims["major_d"], 3.0)
        self.assertEqual(dims["length"], 8.0)
        self.assertEqual(dims["pitch"], 0.5)

    def test_parse_dimension_line_image_no_m_prefix(self):
        """测试照片中常见的 "3*10" 省略 M 写法."""
        dims = _parse_dimension_line_image("3*10 牙距0.5")
        self.assertEqual(dims["major_d"], 3.0)
        self.assertEqual(dims["length"], 10.0)
        self.assertEqual(dims["pitch"], 0.5)

    def test_length_ocr_error_correction(self):
        """测试 OCR 把标题 M4*6 误读为 M4*33 时，能用 mm 值修正为 6."""
        text = "M4*33 牙距0.7 螺杆长度6mm 头部直径7.2mm 头部厚度4mm 对边3mm"
        dims = _parse_dimension_line_image(text)
        self.assertEqual(dims["major_d"], 4.0)
        self.assertEqual(dims["length"], 6.0)

    def test_length_fallback_when_title_missing(self):
        """测试标题未被识别时，能从 mm 值中兜底得到标准长度."""
        # 模拟真实 OCR 输出片段
        text = "M4 33mm 6mm 7.2mm 4mm 3mm 60"
        dims = _parse_dimension_line_image(text)
        self.assertEqual(dims["major_d"], 4.0)
        self.assertEqual(dims["length"], 6.0)
        self.assertEqual(dims["head_d"], 7.2)

    def test_head_h_fallback_excludes_pitch(self):
        """测试头高兜底不会误把螺距当作头高."""
        dims = _parse_dimension_line_image("M3 牙距0.5 头部直径7mm 头部厚度1.5mm")
        # 中文标签应能识别
        self.assertEqual(dims["head_h"], 1.5)
        self.assertEqual(dims["head_d"], 7.0)

    def test_detect_head_type_image_daobian(self):
        """测试 "倒边" 识别为 countersunk."""
        self.assertEqual(_detect_head_type_image("倒边十字螺丝"), "countersunk")

    def test_detect_head_type_image(self):
        """测试照片头型识别."""
        self.assertEqual(_detect_head_type_image("这是一颗盘头螺丝"), "pan")
        self.assertEqual(_detect_head_type_image("内六角杯头螺丝"), "socket")

    def test_detect_drive_type_image(self):
        """测试照片驱动识别."""
        self.assertEqual(_detect_drive_type_image("十字槽螺丝"), "cross")
        self.assertEqual(_detect_drive_type_image("内六角螺丝"), "hex")

    def test_detect_tail_type_image(self):
        """测试照片尾部识别."""
        self.assertEqual(_detect_tail_type_image("尖尾自攻螺丝"), "sharp")
        self.assertEqual(_detect_tail_type_image("平尾螺丝"), "flat")

    def test_parse_spec_from_text(self):
        """测试从 OCR 文本解析完整规格."""
        spec = _parse_spec_from_text("M3x8 盘头 十字 平尾")
        self.assertEqual(spec["major_d"], 3.0)
        self.assertEqual(spec["length"], 8.0)
        self.assertEqual(spec["head_type"], "pan")
        self.assertEqual(spec["drive_type"], "cross")
        self.assertEqual(spec["tail_type"], "flat")

    @patch("standard_parts_ai.image_parser.pytesseract")
    def test_parse_image_uses_tesseract(self, mock_pytesseract):
        """测试 parse_image 调用 Tesseract 并正确解析（mock）."""
        from standard_parts_ai.image_parser import parse_image

        mock_pytesseract.image_to_string.return_value = "M4x10 盘头 十字 尖尾"
        # 这里不需要真实图片，通过 patch Image.open 来提供 fake 图片
        from unittest.mock import MagicMock

        mock_img = MagicMock()
        mock_img.__enter__ = MagicMock(return_value=mock_img)
        mock_img.__exit__ = MagicMock(return_value=False)
        mock_img.convert.return_value = mock_img
        mock_img.filter.return_value = mock_img
        mock_img.resize.return_value = mock_img
        mock_img.getdata.return_value = [128] * (100 * 100)
        mock_img.size = (100, 100)
        mock_img.width = 100
        mock_img.height = 100

        with (patch("standard_parts_ai.image_parser.Image.open", return_value=mock_img),
              patch("standard_parts_ai.image_parser.ImageOps") as mock_imgops):
            mock_imgops.autocontrast.return_value = mock_img
            params = parse_image(Path("fake.jpg"))

        self.assertEqual(params.major_d, 4.0)
        self.assertEqual(params.length, 10.0)
        self.assertEqual(params.head_type, "pan")
        self.assertEqual(params.drive_type, "cross")
        self.assertEqual(params.tail_type, "sharp")


if __name__ == "__main__":
    unittest.main()
