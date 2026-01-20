# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time
from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests import warmup
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestCheckCollisionStress(TransactionCase):
    """
    Stress tests for _check_collision / _check_attendances_variable.

    The collision tree grows exponentially when recurrences share common dates:
    with N mutually-colliding recurrent attendances, level k of the tree contains
    C(N, k+1) nodes, for a total of 2^N - 1 nodes. The algorithm caps at 1000
    nodes to prevent runaway computation.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Stress Test Calendar',
            'calendar_type': 'variable',
        })

    def setUp(self):
        super().setUp()
        self.calendar.attendance_ids.unlink()

    @warmup
    def test_stress_9_colliding_recurrences_duration_based(self):
        """9 mutually-colliding duration-based recurrences -> 2^9-1 = 511 tree nodes.

        Duration-based with 1h each -> 9h total < 24h -> no constraint violation.
        """
        vals = [{
            'calendar_id': self.calendar.id,
            'duration_hours': 1,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_until': date(2025, 12, 31),
        } for _ in range(9)]

        # ~0.070s — 511 tree nodes, 1 query for search + 1 for create
        with self.assertQueryCount(default=15):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create(vals)
            _logger.info("test_stress_9_colliding_recurrences_duration_based: --- %s seconds ---", time.time() - start_time)

    @warmup
    def test_stress_9_colliding_recurrences_time_based(self):
        """Time-based variant: slots staggered (0-1, 1-2, ..., 8-9) so _check_overlap passes."""
        vals = [{
            'calendar_id': self.calendar.id,
            'hour_from': i,
            'hour_to': i + 1,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_until': date(2025, 12, 31),
        } for i in range(9)]

        # ~0.070s — 511 tree nodes, same query pattern as duration-based
        with self.assertQueryCount(default=15):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create(vals)
            _logger.info("test_stress_9_colliding_recurrences_time_based: --- %s seconds ---", time.time() - start_time)

    def test_stress_10_colliding_recurrences_hits_cap(self):
        """10 mutually-colliding recurrences -> 2^10-1 = 1023 > 1000 -> Too Complex.

        Tree explodes at level 7 (cumulative: 10+45+120+210+252+210+120+45 = 1012).
        """
        vals = [{
            'calendar_id': self.calendar.id,
            'duration_hours': 1,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_until': date(2025, 12, 31),
        } for _ in range(10)]

        start_time = time.time()
        with self.assertRaises(UserError):
            self.env['resource.calendar.attendance'].create(vals)
        _logger.info("test_stress_10_colliding_recurrences_hits_cap: --- %s seconds ---", time.time() - start_time)

    @warmup
    def test_stress_200_non_colliding_recurrences(self):
        """200 non-colliding recurrences -> 200 leaves, 19900 null comparisons.

        period=1000 days, start dates offset by 1 day each:
        gcd(1000, 1000) = 1000, delta in [1..199] -> delta % 1000 != 0 -> no collision.
        """
        vals = [{
            'calendar_id': self.calendar.id,
            'duration_hours': 1,
            'recurrency': True,
            'recurrency_interval': 1000,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1) + timedelta(days=i),
            'recurrency_until': date(2030, 12, 31),
        } for i in range(200)]

        # ~0.100s — tree stays flat at 200 leaves, 19900 pairwise checks all returning None
        with self.assertQueryCount(default=17):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create(vals)
            _logger.info("test_stress_200_non_colliding_recurrences: --- %s seconds ---", time.time() - start_time)

    @warmup
    def test_stress_adhoc_against_max_collision_tree(self):
        """Ad-hoc attendance added when 9 colliding recurrences already exist.

        511-node tree must be rebuilt; ad-hoc date matched against each node O(tree_size).
        """
        self.env['resource.calendar.attendance'].create([{
            'calendar_id': self.calendar.id,
            'duration_hours': 1,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_until': date(2025, 12, 31),
        } for _ in range(9)])

        # ~0.070s — rebuilds the 511-node tree + scans it for the ad-hoc date
        with self.assertQueryCount(default=7):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create({
                'calendar_id': self.calendar.id,
                'duration_hours': 1,
                'date': date(2025, 6, 15),
            })
            _logger.info("test_stress_adhoc_against_max_collision_tree: --- %s seconds ---", time.time() - start_time)

    @warmup
    def test_stress_many_adhoc_no_recurrences(self):
        """500 ad-hoc attendances on distinct dates, no recurrences -> no tree built."""
        vals = [{
            'calendar_id': self.calendar.id,
            'duration_hours': 4,
            'date': date(2025, 1, 1) + timedelta(days=i),
        } for i in range(500)]

        # ~0.040s — no tree to build, just 500 ad-hoc grouped by date
        with self.assertQueryCount(default=28):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create(vals)
            _logger.info("test_stress_many_adhoc_no_recurrences: --- %s seconds ---", time.time() - start_time)

    @warmup
    def test_stress_many_adhoc_with_collision_tree(self):
        """100 ad-hoc attendances each scanned against a 127-node collision tree.

        7 colliding recurrences -> 2^7-1 = 127 tree nodes.
        Each ad-hoc is checked against all 127 nodes.
        """
        self.env['resource.calendar.attendance'].create([{
            'calendar_id': self.calendar.id,
            'duration_hours': 1,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'days',
            'date': date(2025, 1, 1),
            'recurrency_until': date(2025, 12, 31),
        } for _ in range(7)])

        vals = [{
            'calendar_id': self.calendar.id,
            'duration_hours': 1,
            'date': date(2025, 3, 1) + timedelta(days=i),
        } for i in range(100)]

        # ~0.030s — 127 tree nodes * 100 ad-hoc dates scanned
        with self.assertQueryCount(default=7):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create(vals)
            _logger.info("test_stress_many_adhoc_with_collision_tree: --- %s seconds ---", time.time() - start_time)

    @warmup
    def test_stress_weekly_recurrences_partial_collision(self):
        """7 weekly recurrences one per weekday (Mon-Sun): each day has exactly 1 -> no growth.

        Same-day pairs would collide (period=7, delta=0 -> delta%7=0), but since
        each day has exactly 1 recurrence, tree stays at 7 leaves.
        """
        vals = [{
            'calendar_id': self.calendar.id,
            'duration_hours': 4,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'weeks',
            'date': date(2025, 1, 6) + timedelta(days=i),  # Mon Jan 6 through Sun Jan 12
            'recurrency_until': date(2025, 12, 31),
        } for i in range(7)]

        # ~0.005s — 7 leaves, 21 pairwise checks all returning None
        with self.assertQueryCount(default=15):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create(vals)
            _logger.info("test_stress_weekly_recurrences_partial_collision: --- %s seconds ---", time.time() - start_time)

    @warmup
    def test_stress_weekly_recurrences_all_same_day_collide(self):
        """9 weekly recurrences all on same weekday -> 2^9-1 = 511 tree nodes.

        period=7 for all, same start date -> gcd=7, delta=0 -> full collision.
        """
        vals = [{
            'calendar_id': self.calendar.id,
            'duration_hours': 1,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'weeks',
            'date': date(2025, 1, 6),  # Monday
            'recurrency_until': date(2025, 12, 31),
        } for _ in range(9)]

        # ~0.070s — 511 tree nodes, same as daily colliding case
        with self.assertQueryCount(default=15):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create(vals)
            _logger.info("test_stress_weekly_recurrences_all_same_day_collide: --- %s seconds ---", time.time() - start_time)

    @warmup
    def test_stress_realistic_complex_calendar(self):
        """Realistic variable calendar for an employee with alternating 2-week schedule.

        Week A (bi-weekly from Mon Jan 6 2025) — full time:
          Mon-Fri  8h-12h  morning   (5 recurrences, every 2 weeks)
          Mon-Fri  13h-17h afternoon (5 recurrences, every 2 weeks)

        Week B (bi-weekly from Mon Jan 13 2025) — 4/5 days:
          Mon-Thu  8h-12h  morning   (4 recurrences)
          Mon-Wed  13h-17h afternoon (3 recurrences)
          Thu      13h-15h short pm  (1 recurrence)

        Training: every 5 days from Jan 7, 17h30-19h (1 recurrence)
        Team meeting: every Monday 12h-13h (1 weekly recurrence)
        Saturday on-call: every 3 weeks from Jan 11, 9h-12h (1 recurrence)

        Ad-hoc:
          - Overtime Wed evening Mar 12 (18h-20h)
          - Extra work Fri Feb 14 in week B (normally off), morning + afternoon
          - Extra Saturday morning Apr 12

        Total: 21 recurrent + 4 ad-hoc = 25 attendances.

        Worst-case day collision: ~4 recurrences (Monday week A = morning + afternoon +
        meeting + training if aligned). Tree stays well under 1000 nodes because
        period-14 leaves only collide with same-day counterparts (gcd(14,14)=14,
        needs delta%14=0), and cross-period collisions (training period=5, meeting
        period=7) have limited fan-out.
        """
        week_a_monday = date(2025, 1, 6)
        week_b_monday = date(2025, 1, 13)
        recurrences = []

        # -- Week A: Mon-Fri full days, bi-weekly --
        for day in range(5):
            recurrences += [
                {
                    'calendar_id': self.calendar.id,
                    'hour_from': 8, 'hour_to': 12,
                    'recurrency': True,
                    'recurrency_interval': 2,
                    'recurrency_type': 'weeks',
                    'date': week_a_monday + timedelta(days=day),
                    'recurrency_until': date(2025, 12, 31),
                },
                {
                    'calendar_id': self.calendar.id,
                    'hour_from': 13, 'hour_to': 17,
                    'recurrency': True,
                    'recurrency_interval': 2,
                    'recurrency_type': 'weeks',
                    'date': week_a_monday + timedelta(days=day),
                    'recurrency_until': date(2025, 12, 31),
                },
            ]

        # -- Week B: Mon-Thu mornings, Mon-Wed afternoons, Thu short pm --
        for day in range(4):
            recurrences.append({
                'calendar_id': self.calendar.id,
                'hour_from': 8, 'hour_to': 12,
                'recurrency': True,
                'recurrency_interval': 2,
                'recurrency_type': 'weeks',
                'date': week_b_monday + timedelta(days=day),
                'recurrency_until': date(2025, 12, 31),
            })
        for day in range(3):
            recurrences.append({
                'calendar_id': self.calendar.id,
                'hour_from': 13, 'hour_to': 17,
                'recurrency': True,
                'recurrency_interval': 2,
                'recurrency_type': 'weeks',
                'date': week_b_monday + timedelta(days=day),
                'recurrency_until': date(2025, 12, 31),
            })
        recurrences.append({  # Thursday short afternoon
            'calendar_id': self.calendar.id,
            'hour_from': 13, 'hour_to': 15,
            'recurrency': True,
            'recurrency_interval': 2,
            'recurrency_type': 'weeks',
            'date': week_b_monday + timedelta(days=3),
            'recurrency_until': date(2025, 12, 31),
        })

        # -- Training: every 5 days, 17h30-19h --
        recurrences.append({
            'calendar_id': self.calendar.id,
            'hour_from': 17.5, 'hour_to': 19,
            'recurrency': True,
            'recurrency_interval': 5,
            'recurrency_type': 'days',
            'date': date(2025, 1, 7),
            'recurrency_until': date(2025, 12, 31),
        })

        # -- Team meeting: every Monday 12h-13h --
        recurrences.append({
            'calendar_id': self.calendar.id,
            'hour_from': 12, 'hour_to': 13,
            'recurrency': True,
            'recurrency_interval': 1,
            'recurrency_type': 'weeks',
            'date': date(2025, 1, 6),
            'recurrency_until': date(2025, 12, 31),
        })

        # -- Saturday on-call: every 3 weeks, 9h-12h --
        recurrences.append({
            'calendar_id': self.calendar.id,
            'hour_from': 9, 'hour_to': 12,
            'recurrency': True,
            'recurrency_interval': 3,
            'recurrency_type': 'weeks',
            'date': date(2025, 1, 11),
            'recurrency_until': date(2025, 12, 31),
        })

        # -- Ad-hoc one-off adjustments --
        adhoc = [
            # Overtime Wednesday evening (week B Wed, no overlap with 13-17)
            {'calendar_id': self.calendar.id, 'hour_from': 18, 'hour_to': 20, 'date': date(2025, 3, 12)},
            # Extra Friday in week B (normally no Friday work)
            {'calendar_id': self.calendar.id, 'hour_from': 8, 'hour_to': 12, 'date': date(2025, 2, 14)},
            {'calendar_id': self.calendar.id, 'hour_from': 13, 'hour_to': 17, 'date': date(2025, 2, 14)},
            # Extra Saturday (not an on-call week)
            {'calendar_id': self.calendar.id, 'hour_from': 8, 'hour_to': 12, 'date': date(2025, 4, 12)},
        ]

        self.assertEqual(len(recurrences), 21)

        # ~0.020s — 21 recurrent leaves, limited cross-period fan-out, tree << 1000 nodes
        with self.assertQueryCount(default=16):
            start_time = time.time()
            self.env['resource.calendar.attendance'].create(recurrences + adhoc)
            _logger.info("test_stress_realistic_complex_calendar: --- %s seconds ---", time.time() - start_time)
