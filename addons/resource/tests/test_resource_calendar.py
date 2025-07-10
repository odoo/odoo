# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz
from datetime import datetime

from odoo.tests.common import TransactionCase


class TestResourceCalendar(TransactionCase):

    def test_fully_flexible_attendance_interval_duration(self):
        """
        Test that the duration of a fully flexible attendance interval is correctly computed.
        """
        calendar = self.env['resource.calendar'].create({
            'name': 'Standard Calendar',
            'two_weeks_calendar': False,
        })
        resource = self.env['resource.resource'].create({
            'name': 'Wade Wilson',
            'calendar_id': False,  # Fully-flexible because no calendar is set
            'tz': 'America/New_York',  # -04:00 UTC offset in the summer
        })
        self.env['resource.calendar.attendance'].create({
            'name': 'TEMP',
            'calendar_id': calendar.id,
            'dayofweek': '2',  # Wednesday
            'hour_from': 14,   # 18:00 UTC
            'hour_to': 17,     # 21:00 UTC
            'date_from': datetime(2025, 6, 4, 0, 0, 0).date(),
        })
        UTC = pytz.timezone('UTC')
        start_dt = datetime(2025, 6, 4, 18, 0, 0).astimezone(UTC)
        end_dt = datetime(2025, 6, 4, 21, 0, 0).astimezone(UTC)
        result_per_resource_id = calendar._attendance_intervals_batch(
            start_dt, end_dt, resource
        )
        start, end, attendance = result_per_resource_id[resource.id]._items[0]
        # For a flexible resource, we expect the output times to match the
        # input times exactly, since the resource has no fixed calendar.
        # Further, the dummy attendance that is created should have a duration
        # equal to the difference between the start and end times.
        self.assertEqual(start, start_dt, "Output start time should match the input start time")
        self.assertEqual(end, end_dt, "Output end time should match the input end time")
        self.assertEqual(attendance.duration_hours, 3.0, "Attendance duration should be 3 hours")
        self.assertEqual(attendance.duration_days, 0.125, "Attendance duration should be 0.125 days (3 hours)")

    def test_flexible_employee_work_intervals(self):
        start = datetime(2015, 11, 8, 00, 00, 00, tzinfo=pytz.UTC)
        end = datetime(2015, 11, 21, 23, 59, 59, tzinfo=pytz.UTC)

        calendar = self.env['resource.calendar'].create({
            'name': 'Flexible 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'flexible_hours': True,
        })

        resource = self.env['resource.resource'].create({
            'name': 'Wade Wilson',
            'calendar_id': calendar.id,
            'tz': 'UTC',
        })

        work_intervals, _dummy = resource._get_valid_work_intervals(start, end)

        # flexible employees have the full interval as work intervals
        self.assertEqual(len(work_intervals[resource.id]._items), 1)
        self.assertEqual(work_intervals[resource.id]._items[0][0], start)
        self.assertEqual(work_intervals[resource.id]._items[0][1], end)
