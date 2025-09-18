"""Unit tests for odoo.libs.ir_sequence — no Odoo ORM dependency."""

import unittest
from datetime import datetime

from odoo.libs.ir_sequence import (
    SEQUENCE_DATE_FORMATS,
    build_interpolation_dict,
    format_sequence_number,
    interpolate_template,
)


class TestSequenceDateFormats(unittest.TestCase):
    """Test SEQUENCE_DATE_FORMATS constant."""

    def test_contains_14_keys(self):
        self.assertEqual(len(SEQUENCE_DATE_FORMATS), 14)

    def test_all_values_are_strftime_codes(self):
        for key, fmt in SEQUENCE_DATE_FORMATS.items():
            self.assertTrue(fmt.startswith("%"), f"{key} format must start with %")

    def test_year_format(self):
        self.assertEqual(SEQUENCE_DATE_FORMATS["year"], "%Y")

    def test_month_format(self):
        self.assertEqual(SEQUENCE_DATE_FORMATS["month"], "%m")


class TestBuildInterpolationDict(unittest.TestCase):
    """Test build_interpolation_dict pure function."""

    def setUp(self):
        self.effective = datetime(2025, 3, 15, 10, 30, 45)
        self.range_date = datetime(2025, 1, 1, 0, 0, 0)
        self.now = datetime(2025, 6, 20, 14, 22, 10)

    def test_returns_42_keys(self):
        """14 date formats × 3 prefixes (bare, range_, current_)."""
        d = build_interpolation_dict(self.effective, self.range_date, self.now)
        self.assertEqual(len(d), 42)

    def test_bare_keys_use_effective_date(self):
        d = build_interpolation_dict(self.effective, self.range_date, self.now)
        self.assertEqual(d["year"], "2025")
        self.assertEqual(d["month"], "03")
        self.assertEqual(d["day"], "15")

    def test_range_keys_use_range_date(self):
        d = build_interpolation_dict(self.effective, self.range_date, self.now)
        self.assertEqual(d["range_year"], "2025")
        self.assertEqual(d["range_month"], "01")
        self.assertEqual(d["range_day"], "01")

    def test_current_keys_use_now(self):
        d = build_interpolation_dict(self.effective, self.range_date, self.now)
        self.assertEqual(d["current_year"], "2025")
        self.assertEqual(d["current_month"], "06")
        self.assertEqual(d["current_day"], "20")

    def test_short_year(self):
        d = build_interpolation_dict(self.effective, self.range_date, self.now)
        self.assertEqual(d["y"], "25")

    def test_time_components(self):
        d = build_interpolation_dict(self.effective, self.range_date, self.now)
        self.assertEqual(d["h24"], "10")
        self.assertEqual(d["min"], "30")
        self.assertEqual(d["sec"], "45")

    def test_iso_week_fields(self):
        d = build_interpolation_dict(self.effective, self.range_date, self.now)
        # 2025-03-15 is week 10 (ISO)
        self.assertIn("isoweek", d)
        self.assertIn("isoyear", d)
        self.assertIn("isoy", d)

    def test_all_dates_same(self):
        """When all three dates are the same, all variants should be equal."""
        dt = datetime(2025, 7, 4, 12, 0, 0)
        d = build_interpolation_dict(dt, dt, dt)
        for key in SEQUENCE_DATE_FORMATS:
            self.assertEqual(d[key], d[f"range_{key}"])
            self.assertEqual(d[key], d[f"current_{key}"])


class TestInterpolateTemplate(unittest.TestCase):
    """Test interpolate_template pure function."""

    def test_basic_interpolation(self):
        result = interpolate_template("INV/%(year)s/", {"year": "2025"})
        self.assertEqual(result, "INV/2025/")

    def test_multiple_placeholders(self):
        d = {"year": "2025", "month": "03"}
        result = interpolate_template("%(year)s/%(month)s/", d)
        self.assertEqual(result, "2025/03/")

    def test_none_template(self):
        result = interpolate_template(None, {"year": "2025"})
        self.assertEqual(result, "")

    def test_empty_template(self):
        result = interpolate_template("", {"year": "2025"})
        self.assertEqual(result, "")

    def test_no_placeholders(self):
        result = interpolate_template("STATIC", {"year": "2025"})
        self.assertEqual(result, "STATIC")

    def test_missing_key_raises(self):
        with self.assertRaises(KeyError):
            interpolate_template("%(missing)s", {"year": "2025"})


class TestFormatSequenceNumber(unittest.TestCase):
    """Test format_sequence_number pure function."""

    def test_basic_padding(self):
        self.assertEqual(format_sequence_number(42, 5), "00042")

    def test_zero_padding(self):
        self.assertEqual(format_sequence_number(42, 0), "42")

    def test_number_exceeds_padding(self):
        """Number wider than padding — no truncation."""
        self.assertEqual(format_sequence_number(123456, 3), "123456")

    def test_with_prefix(self):
        self.assertEqual(format_sequence_number(42, 5, prefix="INV/"), "INV/00042")

    def test_with_suffix(self):
        self.assertEqual(format_sequence_number(42, 5, suffix="/A"), "00042/A")

    def test_with_prefix_and_suffix(self):
        result = format_sequence_number(42, 5, prefix="INV/", suffix="/A")
        self.assertEqual(result, "INV/00042/A")

    def test_number_one(self):
        self.assertEqual(format_sequence_number(1, 4), "0001")

    def test_large_number(self):
        self.assertEqual(format_sequence_number(999999, 4), "999999")


if __name__ == "__main__":
    unittest.main()
