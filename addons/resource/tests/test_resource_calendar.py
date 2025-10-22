# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz
from datetime import datetime
from freezegun import freeze_time

from odoo import Command
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

    def test_flexible_calendar_attendance_interval_duration(self):
        """
        Test that the duration of an attendance interval for flexible calendar is correctly computed.
        """
        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'Flexible Calendar',
            'hours_per_day': 7.0,
            'full_time_required_hours': 30,
            'flexible_hours': True,
            'tz': 'UTC',
        })

        # Case 1: get attendances for the full week.
        # Expected: 7-7-7-7-2 (30 hours total)
        expected_hours = [7, 7, 7, 7, 2]

        start_dt = datetime(2025, 6, 2, 0, 0, 0).astimezone(pytz.UTC)
        end_dt = datetime(2025, 6, 7, 23, 59, 59).astimezone(pytz.UTC)
        result_per_resource_id = flexible_calendar._attendance_intervals_batch(
            start_dt, end_dt
        )
        self.assertEqual(expected_hours, [(end - start).total_seconds() / 3600 for start, end, dummy_attendance in result_per_resource_id[0]._items])
        self.assertEqual(expected_hours, [dummy_attendance.duration_hours for start, end, dummy_attendance in result_per_resource_id[0]._items])

        # Case 2: check attendances are all contained between start_dt and end_dt
        start_dt = datetime(2025, 6, 2, 11, 0, 0).astimezone(pytz.UTC)
        end_dt = datetime(2025, 6, 7, 13, 0, 0).astimezone(pytz.UTC)
        result_per_resource_id = flexible_calendar._attendance_intervals_batch(
            start_dt, end_dt
        )

        self.assertTrue(start_dt <= result_per_resource_id[0]._items[0][0], "First attendance interval should not start before start_dt")
        self.assertTrue(end_dt >= result_per_resource_id[0]._items[4][1], "Last attendance interval should not end after end_dt")

    @freeze_time("2019-5-28 08:00:00")
    def test_working_time_holiday_multicompany(self):
        """
        This test checks that there is no issue computing the "working time to assign" even if a holiday has been set
        for this moment, but on another company.
        """
        company_0, company_1 = self.env['res.company'].create([{
            "name": "Test company 0",
        },
            {
                "name": "Test company 1",
            }])

        self.env['resource.calendar.leaves'].create([{
            'name': "Public Holiday for company 0",
            'calendar_id': company_1.resource_calendar_ids.id,
            'company_id': company_1.id,
            'date_from': datetime(2019, 5, 27, 0, 0, 0),
            'date_to': datetime(2019, 5, 29, 23, 0, 0),
            'resource_id': False,
            'time_type': "leave",
        }])
        company_1.resource_calendar_ids.write({"leave_ids": [Command.clear()]})
        duration = company_0.resource_calendar_ids.get_work_duration_data(datetime(2019, 5, 27, 11, 0, 0),
                                                                          datetime(2019, 5, 28, 11, 0, 0),
                                                                          compute_leaves=True)
        self.assertEqual(duration, {'days': 1.0, 'hours': 8.0})
