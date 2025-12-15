# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from datetime import date

from odoo.tests import TransactionCase, tagged

from odoo.addons.hr_work_entry.models.utils import remove_days_from_range


@tagged('-at_install', 'post_install')
class TestRemoveDaysFromRange(TransactionCase):
    """
    remove_days_from_range() is mainly used to split work entries ranges when
    needing to ignore specific days (e.g.: days with validated work entries)
    The function should be able to split a range even if the days are shuffled,
    out of bounds, on bounds, etc.
    """

    def test_basic_split(self):
        days = [
            date(2025, 5, 4),
        ]
        range = {
            'start': date(2025, 5, 1),
            'stop': date(2025, 5, 10),
        }
        expected_ranges = [
            {'start': date(2025, 5, 1), 'stop': date(2025, 5, 3)},
            {'start': date(2025, 5, 5), 'stop': date(2025, 5, 10)},
        ]
        ranges = remove_days_from_range(range, days)
        self.assertEqual(ranges, expected_ranges)

    def test_days_on_bounds(self):
        days = [
            date(2025, 5, 1),
            date(2025, 5, 10),
        ]
        range = {
            'start': date(2025, 5, 1),
            'stop': date(2025, 5, 10),
        }
        expected_ranges = [
            {'start': date(2025, 5, 2), 'stop': date(2025, 5, 9)},
        ]
        ranges = remove_days_from_range(range, days)
        self.assertEqual(ranges, expected_ranges)

    def test_days_out_of_bounds(self):
        days = [
            date(2025, 4, 1),
            date(2025, 5, 11),
        ]
        range = {
            'start': date(2025, 5, 1),
            'stop': date(2025, 5, 10),
        }
        expected_ranges = [range]
        ranges = remove_days_from_range(range, days)
        self.assertEqual(ranges, expected_ranges)

    def test_empty_days(self):
        days = []
        range = {
            'start': date(2025, 5, 1),
            'stop': date(2025, 5, 10),
        }
        expected_ranges = [range]
        ranges = remove_days_from_range(range, days)
        self.assertEqual(ranges, expected_ranges)

    def test_mixed_shuffled(self):
        days = [
            date(2019, 3, 3),  # out of bound
            date(2020, 2, 19),  # out of bound
            date(2020, 2, 20),  # is bound
            date(2021, 5, 11),
            date(2022, 1, 1),
            date(2022, 4, 10),  # is bound
            date(2022, 4, 11),  # out of bound
            date(2023, 3, 2),  # out of bound
        ]
        range = {
            'start': date(2020, 2, 20),
            'stop': date(2022, 4, 10),
        }
        expected_ranges = [
            {'start': date(2020, 2, 21), 'stop': date(2021, 5, 10)},
            {'start': date(2021, 5, 12), 'stop': date(2021, 12, 31)},
            {'start': date(2022, 1, 2), 'stop': date(2022, 4, 9)},
        ]

        # days can be in any order. A seed is specified to make it consistent
        random.seed(0)
        random.shuffle(days)

        ranges = remove_days_from_range(range, days)
        self.assertEqual(ranges, expected_ranges)

    def test_gap_of_one_day(self):
        """
        The function should still work even if a returned range should have the
        same start and stop dates.
        """
        days = [date(2026, 1, 3), date(2026, 1, 5)]
        range = {'start': date(2026, 1, 1), 'stop': date(2026, 1, 7)}
        expected_ranges = [
          {'start': date(2026, 1, 1), 'stop': date(2026, 1, 2)},
          {'start': date(2026, 1, 4), 'stop': date(2026, 1, 4)},
          {'start': date(2026, 1, 6), 'stop': date(2026, 1, 7)},
        ]
        ranges = remove_days_from_range(range, days)
        self.assertEqual(ranges, expected_ranges)
