"""Unit tests for odoo.libs.report_paperformat — no Odoo ORM dependency."""

import unittest

from odoo.libs.report_paperformat import PAPER_SIZES


class TestPaperSizes(unittest.TestCase):
    """Test PAPER_SIZES constant."""

    def test_is_list(self):
        self.assertIsInstance(PAPER_SIZES, list)

    def test_has_entries(self):
        self.assertGreater(len(PAPER_SIZES), 25)

    def test_a4_present(self):
        a4 = next(p for p in PAPER_SIZES if p["key"] == "A4")
        self.assertEqual(a4["width"], 210.0)
        self.assertEqual(a4["height"], 297.0)

    def test_letter_present(self):
        letter = next(p for p in PAPER_SIZES if p["key"] == "Letter")
        self.assertAlmostEqual(letter["width"], 215.9)

    def test_custom_has_no_dimensions(self):
        custom = next(p for p in PAPER_SIZES if p["key"] == "custom")
        self.assertNotIn("width", custom)
        self.assertNotIn("height", custom)

    def test_all_have_key(self):
        for paper in PAPER_SIZES:
            self.assertIn("key", paper)

    def test_all_non_custom_have_dimensions(self):
        for paper in PAPER_SIZES:
            if paper["key"] != "custom":
                self.assertIn("width", paper, f"Missing width for {paper['key']}")
                self.assertIn("height", paper, f"Missing height for {paper['key']}")


if __name__ == "__main__":
    unittest.main()
