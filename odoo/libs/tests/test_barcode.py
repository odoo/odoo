import unittest
from unittest import mock

import odoo.libs.barcode as barcode_module
from odoo.libs.barcode import (
    createBarcodeDrawing,
    get_barcode_font,
    is_barcode_encoding_valid,
)


class TestBarcodeFontInitFallback(unittest.TestCase):
    def setUp(self):
        self._saved_init = barcode_module._barcode_init
        barcode_module._barcode_init = None
        self.addCleanup(self._restore)

    def _restore(self):
        barcode_module._barcode_init = self._saved_init

    def test_falls_back_to_courier_when_font_lookup_raises(self):
        with mock.patch(
            "reportlab.pdfbase.pdfmetrics.TypeFace.findT1File",
            side_effect=RuntimeError("boom"),
        ):
            self.assertEqual(get_barcode_font(), "Courier")

    def test_falls_back_to_courier_when_drawing_render_raises(self):
        with mock.patch(
            "reportlab.graphics.barcode.createBarcodeDrawing",
            side_effect=RuntimeError("boom"),
        ):
            self.assertEqual(get_barcode_font(), "Courier")

    def test_createBarcodeDrawing_delegates_after_init(self):
        drawing = createBarcodeDrawing(
            "Code128", value="foo", format="png", width=10, height=10
        )
        self.assertIsNotNone(drawing)


class TestCheckBarcodeEncoding(unittest.TestCase):
    def test_empty_value_does_not_raise(self):
        self.assertFalse(is_barcode_encoding_valid("", "ean13"))
        self.assertFalse(is_barcode_encoding_valid("", "ean8"))

    def test_unknown_encoding_returns_false(self):
        self.assertFalse(is_barcode_encoding_valid("12345", "code128"))

    def test_valid_ean13(self):
        self.assertTrue(is_barcode_encoding_valid("2022071416014", "ean13"))

    def test_wrong_length_returns_false(self):
        self.assertFalse(is_barcode_encoding_valid("123", "ean13"))

    def test_any_encoding(self):
        self.assertTrue(is_barcode_encoding_valid("whatever", "any"))

    def test_returns_bool(self):
        self.assertIsInstance(is_barcode_encoding_valid("abc", "ean13"), bool)


if __name__ == "__main__":
    unittest.main()


class TestEncodingPredicateIsTotal(unittest.TestCase):
    def test_a_missing_barcode_or_encoding_is_simply_not_valid(self):
        for barcode, encoding in (
            (None, "ean13"),
            (False, "any"),
            (4006381333931, "ean13"),
            ("4006381333931", None),
        ):
            with self.subTest(barcode=barcode, encoding=encoding):
                self.assertFalse(is_barcode_encoding_valid(barcode, encoding))
        self.assertTrue(is_barcode_encoding_valid("4006381333931", "ean13"))
