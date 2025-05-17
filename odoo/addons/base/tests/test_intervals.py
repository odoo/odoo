from datetime import datetime

from odoo.tests.common import TransactionCase
from odoo.tools.intervals import Intervals, intervals_overlap, invert_intervals


class TestIntervals(TransactionCase):

    def ints(self, pairs):
        recs = self.env['base']
        return [(a, b, recs) for a, b in pairs]

    def test_union(self):
        def check(a, b):
            a, b = self.ints(a), self.ints(b)
            self.assertEqual(list(Intervals(a)), b)

        check([(1, 2), (3, 4)], [(1, 2), (3, 4)])
        check([(1, 2), (2, 4)], [(1, 4)])
        check([(1, 3), (2, 4)], [(1, 4)])
        check([(1, 4), (2, 3)], [(1, 4)])
        check([(3, 4), (1, 2)], [(1, 2), (3, 4)])
        check([(2, 4), (1, 2)], [(1, 4)])
        check([(2, 4), (1, 3)], [(1, 4)])
        check([(2, 3), (1, 4)], [(1, 4)])

    def test_intersection(self):
        def check(a, b, c):
            a, b, c = self.ints(a), self.ints(b), self.ints(c)
            self.assertEqual(list(Intervals(a) & Intervals(b)), c)

        check([(10, 20)], [(5, 8)], [])
        check([(10, 20)], [(5, 10)], [])
        check([(10, 20)], [(5, 15)], [(10, 15)])
        check([(10, 20)], [(5, 20)], [(10, 20)])
        check([(10, 20)], [(5, 25)], [(10, 20)])
        check([(10, 20)], [(10, 15)], [(10, 15)])
        check([(10, 20)], [(10, 20)], [(10, 20)])
        check([(10, 20)], [(10, 25)], [(10, 20)])
        check([(10, 20)], [(15, 18)], [(15, 18)])
        check([(10, 20)], [(15, 20)], [(15, 20)])
        check([(10, 20)], [(15, 25)], [(15, 20)])
        check([(10, 20)], [(20, 25)], [])
        check(
            [(0, 5), (10, 15), (20, 25), (30, 35)],
            [(6, 7), (9, 12), (13, 17), (22, 23), (24, 40)],
            [(10, 12), (13, 15), (22, 23), (24, 25), (30, 35)],
        )

    def test_difference(self):
        def check(a, b, c):
            a, b, c = self.ints(a), self.ints(b), self.ints(c)
            self.assertEqual(list(Intervals(a) - Intervals(b)), c)

        check([(10, 20)], [(5, 8)], [(10, 20)])
        check([(10, 20)], [(5, 10)], [(10, 20)])
        check([(10, 20)], [(5, 15)], [(15, 20)])
        check([(10, 20)], [(5, 20)], [])
        check([(10, 20)], [(5, 25)], [])
        check([(10, 20)], [(10, 15)], [(15, 20)])
        check([(10, 20)], [(10, 20)], [])
        check([(10, 20)], [(10, 25)], [])
        check([(10, 20)], [(15, 18)], [(10, 15), (18, 20)])
        check([(10, 20)], [(15, 20)], [(10, 15)])
        check([(10, 20)], [(15, 25)], [(10, 15)])
        check([(10, 20)], [(20, 25)], [(10, 20)])
        check(
            [(0, 5), (10, 15), (20, 25), (30, 35)],
            [(6, 7), (9, 12), (13, 17), (22, 23), (24, 40)],
            [(0, 5), (12, 13), (20, 22), (23, 24)],
        )


class TestUtils(TransactionCase):

    def test_intervals_intersections(self):
        test_data = [
            ((datetime(2023, 2, 14), datetime(2023, 2, 15)),
             (datetime(2023, 2, 15), datetime(2023, 2, 16)), False),
            ((datetime(2023, 2, 14), datetime(2023, 2, 15)),
             (datetime(2023, 2, 13), datetime(2023, 2, 16)), True),
            ((datetime(2023, 2, 13), datetime(2023, 2, 16)),
             (datetime(2023, 2, 14), datetime(2023, 2, 15)), True),
            ((datetime(2023, 2, 13), datetime(2023, 2, 16)),
             (datetime(2023, 2, 15), datetime(2023, 2, 17)), True),
        ]
        for interval_a, interval_b, overlaps in test_data:
            with self.subTest(interval_a=interval_a, interval_b=interval_b):
                self.assertEqual(intervals_overlap(
                    interval_a, interval_b), overlaps)

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


class TestKeepDistinctIntervals(TransactionCase):

    def ints(self, pairs):
        recs = self.env['base']
        return [(a, b, recs) for a, b in pairs]

    def test_union(self):
        def check(a, b):
            a, b = self.ints(a), self.ints(b)
            self.assertEqual(list(Intervals(a, keep_distinct=True)), b)

        check([(1, 2), (3, 4)], [(1, 2), (3, 4)])
        check([(1, 2), (2, 4)], [(1, 2), (2, 4)])
        check([(1, 3), (2, 4)], [(1, 4)])
        check([(1, 4), (2, 3)], [(1, 4)])
        check([(1, 4), (1, 4)], [(1, 4)])
        check([(3, 4), (1, 2)], [(1, 2), (3, 4)])
        check([(2, 4), (1, 2)], [(1, 2), (2, 4)])
        check([(2, 4), (1, 3)], [(1, 4)])
        check([(2, 3), (1, 4)], [(1, 4)])

    def test_intersection(self):
        def check(a, b, c):
            a, b, c = self.ints(a), self.ints(b), self.ints(c)
            self.assertEqual(list(Intervals(a, keep_distinct=True) & Intervals(b, keep_distinct=True)), c)

        check([(10, 20)], [(5, 8)], [])
        check([(10, 20)], [(5, 10)], [])
        check([(10, 20)], [(5, 15)], [(10, 15)])
        check([(10, 20)], [(5, 20)], [(10, 20)])
        check([(10, 20)], [(5, 25)], [(10, 20)])
        check([(10, 20)], [(10, 15)], [(10, 15)])
        check([(10, 20)], [(10, 20)], [(10, 20)])
        check([(10, 20)], [(10, 25)], [(10, 20)])
        check([(10, 20)], [(15, 18)], [(15, 18)])
        check([(10, 20)], [(15, 20)], [(15, 20)])
        check([(10, 20)], [(15, 25)], [(15, 20)])
        check([(10, 20)], [(20, 25)], [])
        check(
            [(0, 5), (10, 15), (20, 25), (30, 35)],
            [(6, 7), (9, 12), (13, 17), (22, 23), (24, 40)],
            [(10, 12), (13, 15), (22, 23), (24, 25), (30, 35)],
        )

    def test_difference(self):
        def check(a, b, c):
            a, b, c = self.ints(a), self.ints(b), self.ints(c)
            self.assertEqual(list(Intervals(a, keep_distinct=True) - Intervals(b, keep_distinct=True)), c)

        check([(10, 20)], [(5, 8)], [(10, 20)])
        check([(10, 20)], [(5, 10)], [(10, 20)])
        check([(10, 20)], [(5, 15)], [(15, 20)])
        check([(10, 20)], [(5, 20)], [])
        check([(10, 20)], [(5, 25)], [])
        check([(10, 20)], [(10, 15)], [(15, 20)])
        check([(10, 20)], [(10, 20)], [])
        check([(10, 20)], [(10, 25)], [])
        check([(10, 20)], [(15, 18)], [(10, 15), (18, 20)])
        check([(10, 20)], [(15, 20)], [(10, 15)])
        check([(10, 20)], [(15, 25)], [(10, 15)])
        check([(10, 20)], [(20, 25)], [(10, 20)])
        check(
            [(0, 5), (10, 15), (20, 25), (30, 35)],
            [(6, 7), (9, 12), (13, 17), (22, 23), (24, 40)],
            [(0, 5), (12, 13), (20, 22), (23, 24)],
        )
