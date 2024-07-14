from datetime import datetime

from odoo.tests.common import BaseCase
from odoo.addons.appointment.utils import intervals_overlap, invert_intervals

class TestAppointmentIntervalUtils(BaseCase):
    def test_intervals_intersections(self):
        test_data = [
            ((datetime(2023, 2, 14), datetime(2023, 2, 15)), (datetime(2023, 2, 15), datetime(2023, 2, 16)), False),
            ((datetime(2023, 2, 14), datetime(2023, 2, 15)), (datetime(2023, 2, 13), datetime(2023, 2, 16)), True),
            ((datetime(2023, 2, 13), datetime(2023, 2, 16)), (datetime(2023, 2, 14), datetime(2023, 2, 15)), True),
            ((datetime(2023, 2, 13), datetime(2023, 2, 16)), (datetime(2023, 2, 15), datetime(2023, 2, 17)), True),
        ]
        for interval_a, interval_b, overlaps in test_data:
            with self.subTest(interval_a=interval_a, interval_b=interval_b):
                self.assertEqual(intervals_overlap(interval_a, interval_b), overlaps)

    def test_intervals_inversion(self):
        test_intervals = [
            (datetime(2023, 2, 5), datetime(2023, 2, 6)),  # no adjacent
            (datetime(2023, 2, 7), datetime(2023, 2, 7)),  # 0-length
            (datetime(2023, 2, 9), datetime(2023, 2, 10)),  # multi-adjacent
            (datetime(2023, 2, 10), datetime(2023, 2, 11)),
            (datetime(2023, 2, 11), datetime(2023, 2, 12)),
            (datetime(2023, 2, 13), datetime(2023, 2, 15)),  # overlapping
            (datetime(2023, 2, 14), datetime(2023, 2, 18)),
            (datetime(2023, 2, 15), datetime(2023, 2, 16)),  # contained inside the previous
            (datetime(2023, 2, 25), datetime(2023, 3, 10)),  # unordered non-adjacent
            (datetime(2023, 2, 20), datetime(2023, 2, 22)),
        ]
        test_limits = [
            (datetime(2023, 1, 1), datetime(2023, 4, 1)),  # all-encompassing
            (datetime(2023, 2, 5), datetime(2023, 3, 10)),  # exact fit original intervals
            (datetime(2023, 2, 9), datetime(2023, 2, 12)),  # exact fit of one interval
            (datetime(2023, 2, 6), datetime(2023, 2, 9)),  # exact fit of one inverted interval
            (datetime(2023, 2, 8), datetime(2023, 2, 11)),  # overlapping some
        ]
        test_results = [
            [
                (datetime(2023, 1, 1), datetime(2023, 2, 5)),
                (datetime(2023, 2, 6), datetime(2023, 2, 9)),
                (datetime(2023, 2, 12), datetime(2023, 2, 13)),
                (datetime(2023, 2, 18), datetime(2023, 2, 20)),
                (datetime(2023, 2, 22), datetime(2023, 2, 25)),
                (datetime(2023, 3, 10), datetime(2023, 4, 1)),
            ],
            [
                (datetime(2023, 2, 6), datetime(2023, 2, 9)),
                (datetime(2023, 2, 12), datetime(2023, 2, 13)),
                (datetime(2023, 2, 18), datetime(2023, 2, 20)),
                (datetime(2023, 2, 22), datetime(2023, 2, 25)),
            ],
            [],
            [
                (datetime(2023, 2, 6), datetime(2023, 2, 9)),
            ],
            [
                (datetime(2023, 2, 8), datetime(2023, 2, 9)),
            ],
        ]
        for limits, expected_result in zip(test_limits, test_results):
            start, end = limits
            with self.subTest(start=start, end=end):
                self.assertListEqual(invert_intervals(test_intervals, start, end), expected_result)
