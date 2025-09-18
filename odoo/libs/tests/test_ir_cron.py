"""Unit tests for odoo.libs.ir_cron — no Odoo ORM dependency."""

import unittest
from enum import StrEnum

from dateutil.relativedelta import relativedelta

from odoo.libs.ir_cron import CompletionStatus, interval_delta


class TestCompletionStatus(unittest.TestCase):
    """Test CompletionStatus StrEnum."""

    def test_is_str_enum(self):
        self.assertTrue(issubclass(CompletionStatus, StrEnum))

    def test_values(self):
        self.assertEqual(CompletionStatus.FULLY_DONE, "fully done")
        self.assertEqual(CompletionStatus.PARTIALLY_DONE, "partially done")
        self.assertEqual(CompletionStatus.FAILED, "failed")

    def test_string_equality(self):
        """StrEnum members must compare equal to their string values."""
        self.assertTrue(CompletionStatus.FULLY_DONE == "fully done")
        self.assertTrue(CompletionStatus.FAILED == "failed")

    def test_is_string(self):
        self.assertIsInstance(CompletionStatus.FULLY_DONE, str)

    def test_members_count(self):
        self.assertEqual(len(CompletionStatus), 3)


class TestIntervalDelta(unittest.TestCase):
    """Test interval_delta function."""

    def test_minutes(self):
        result = interval_delta("minutes", 30)
        self.assertEqual(result, relativedelta(minutes=30))

    def test_hours(self):
        result = interval_delta("hours", 2)
        self.assertEqual(result, relativedelta(hours=2))

    def test_days(self):
        result = interval_delta("days", 7)
        self.assertEqual(result, relativedelta(days=7))

    def test_weeks(self):
        result = interval_delta("weeks", 2)
        self.assertEqual(result, relativedelta(weeks=2))

    def test_months(self):
        result = interval_delta("months", 3)
        self.assertEqual(result, relativedelta(months=3))

    def test_unknown_type_raises(self):
        with self.assertRaises(KeyError):
            interval_delta("years", 1)

    def test_zero_interval(self):
        result = interval_delta("days", 0)
        self.assertEqual(result, relativedelta(days=0))

    def test_negative_interval(self):
        result = interval_delta("hours", -1)
        self.assertEqual(result, relativedelta(hours=-1))


if __name__ == "__main__":
    unittest.main()
