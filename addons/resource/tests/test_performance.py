# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from odoo.tests import warmup
from odoo.tests.common import TransactionCase


class TestFlexibleResourceCalendarPerformance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.flexible_calendar = cls.env['resource.calendar'].create({
            'name': 'Test Flexible Calendar',
            'calendar_type': 'flexible',
            'attendance_ids': [
                (0, 0, {
                    'date': date(1, 1, 1) + timedelta(days=d, weeks=w),
                    'hour_from': h[0],
                    'hour_to': h[1],
                    'recurrency': True,
                    'recurrency_type': 'weeks',
                    'recurrency_interval': 2,
                    })
                for d in range(5) for w in range(2) for h in [(8, 12), (13, 17)]
            ]
        })

    @warmup
    def test_performance_attendance_intervals_batch_flexible_calendar(self):
        tz = ZoneInfo('UTC')
        start_dt = datetime(2023, 1, 1, 0, 0, 0, tzinfo=tz)
        end_dt = datetime(2023, 12, 31, 23, 59, 59, tzinfo=tz)
        with self.assertQueryCount(5):
            self.flexible_calendar._attendance_intervals_batch(start_dt, end_dt)
