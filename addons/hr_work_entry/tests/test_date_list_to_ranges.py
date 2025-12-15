# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_work_entry.models.utils import date_list_to_ranges


@tagged('-at_install', 'post_install')
class TestDateListToRanges(TransactionCase):
    """
    date_list_to_ranges() is used to mege all neighboring days into range.
    It's mainly used for work entries generation. This test ensures the function
    works in some specific cases.
    """
    def test_basic_case(self):
        days = [
            date(2025, 5, 2),
            date(2025, 5, 3),
            date(2025, 5, 4),
            date(2025, 6, 6),
            date(2025, 6, 7),
        ]
        expected_ranges = [
            {'start': date(2025, 5, 2), 'stop': date(2025, 5, 4)},
            {'start': date(2025, 6, 6), 'stop': date(2025, 6, 7)},
        ]
        ranges = date_list_to_ranges(days)
        self.assertEqual(ranges, expected_ranges)

    def test_basic_case_string(self):
        """
        _date_list_to_ranges should be able to convert the dates when needed
        This is useful when calling the date objects have beeen created in the
        frontend
        """
        days = [
            '2025-5-2',
            '2025-5-3',
            '2025-5-4',
            '2025-6-6',
            '2025-6-7',
        ]
        expected_ranges = [
            {'start': date(2025, 5, 2), 'stop': date(2025, 5, 4)},
            {'start': date(2025, 6, 6), 'stop': date(2025, 6, 7)},
        ]
        ranges = date_list_to_ranges(days)
        self.assertEqual(ranges, expected_ranges)

    def test_no_days(self):
        days = []
        expected_ranges = []
        ranges = date_list_to_ranges(days)
        self.assertEqual(ranges, expected_ranges)

    def test_single_day(self):
        days = [date(2003, 11, 6)]
        expected_ranges = [
            {'start': date(2003, 11, 6), 'stop': date(2003, 11, 6)},
        ]
        ranges = date_list_to_ranges(days)
        self.assertEqual(ranges, expected_ranges)

    def test_duplicate_days(self):
        days = [
            date(2003, 11, 6),
            date(2003, 11, 7),
            date(2003, 11, 7),
            date(2003, 11, 8),
        ]
        expected_ranges = [
            {'start': date(2003, 11, 6), 'stop': date(2003, 11, 8)},
        ]
        ranges = date_list_to_ranges(days)
        self.assertEqual(ranges, expected_ranges)

    def test_mixed_days(self):
        days = [
            date(2020, 5, 4),
            date(2025, 5, 2),
            date(2020, 5, 2),
            date(2025, 5, 4),
            date(2003, 11, 6),
            '2025-06-06',
            date(2020, 5, 3),
            date(2025, 5, 3),
            date(2025, 6, 7),
            date(2020, 5, 3),
        ]
        expected_ranges = [
            {'start': date(2003, 11, 6), 'stop': date(2003, 11, 6)},
            {'start': date(2020, 5, 2), 'stop': date(2020, 5, 4)},
            {'start': date(2025, 5, 2), 'stop': date(2025, 5, 4)},
            {'start': date(2025, 6, 6), 'stop': date(2025, 6, 7)},
        ]
        ranges = date_list_to_ranges(days)
        self.assertEqual(ranges, expected_ranges)
