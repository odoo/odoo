# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, UTC
from zoneinfo import ZoneInfo

from odoo.tests.common import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResourceCalendar(TransactionCase):

    def test_fully_flexible_attendance_interval_duration(self):
        """
        Test that the duration of a fully flexible attendance interval is correctly computed.
        """
        calendar = self.env['resource.calendar'].create({
            'name': 'Standard Calendar',
        })
        resource = self.env['resource.resource'].create({
            'name': 'Wade Wilson',
            'calendar_id': False,  # Fully-flexible because no calendar is set
            'tz': 'America/New_York',  # -04:00 UTC offset in the summer
        })
        self.env['resource.calendar.attendance'].create({
            'calendar_id': calendar.id,
            'dayofweek': '2',  # Wednesday
            'hour_from': 14,   # 18:00 UTC
            'hour_to': 17,     # 21:00 UTC
        })
        start_dt = datetime(2025, 6, 4, 18, 0, 0).astimezone(UTC)
        end_dt = datetime(2025, 6, 4, 21, 0, 0).astimezone(UTC)
        resources_per_tz = {
            ZoneInfo('America/New_York'): resource
        }
        result_per_resource_id = calendar._attendance_intervals_batch(
            start_dt, end_dt, resources_per_tz
        )
        start, end, attendance = result_per_resource_id[resource.id]._items[0]
        # For a flexible resource, we expect the output times to match the
        # input times exactly, since the resource has no fixed calendar.
        # Further, the dummy attendance that is created should have a duration
        # equal to the difference between the start and end times.
        self.assertEqual(start, start_dt, "Output start time should match the input start time")
        self.assertEqual(end, end_dt, "Output end time should match the input end time")
        self.assertEqual(attendance.duration_hours, 3.0, "Attendance duration should be 3 hours")

    def test_flexible_calendar_attendance_interval_duration(self):
        """
        Test that the duration of an attendance interval for flexible calendar is correctly computed.
        """
        flex_resource = self.env['resource.resource'].create({
            'name': 'Test FlexResource',
            'calendar_id': False,
            'hours_per_week': 30.0,
            'hours_per_day': 7.0,
            'tz': 'UTC',
        })

        # Case 1: get attendances for the full week.
        # Expected: 7-7-7-7-2 (30 hours total)
        expected_hours = [7, 7, 7, 7, 2]

        start_dt = datetime(2025, 6, 2, 0, 0, 0).astimezone(UTC)
        end_dt = datetime(2025, 6, 7, 23, 59, 59).astimezone(UTC)
        resources_per_tz = {
            UTC: flex_resource
        }
        result_per_resource_id = self.env['resource.calendar']._attendance_intervals_batch(
            start_dt, end_dt, resources_per_tz=resources_per_tz
        )
        self.assertEqual(expected_hours, [(end - start).total_seconds() / 3600 for start, end, dummy_attendance in result_per_resource_id[flex_resource.id]._items])
        self.assertEqual(expected_hours, [dummy_attendance.duration_hours for start, end, dummy_attendance in result_per_resource_id[flex_resource.id]._items])

        # Case 2: check attendances are all contained between start_dt and end_dt
        start_dt = datetime(2025, 6, 2, 11, 0, 0).astimezone(UTC)
        end_dt = datetime(2025, 6, 7, 13, 0, 0).astimezone(UTC)
        result_per_resource_id = self.env['resource.calendar']._attendance_intervals_batch(
            start_dt, end_dt, resources_per_tz=resources_per_tz
        )

        self.assertTrue(start_dt <= result_per_resource_id[flex_resource.id]._items[0][0], "First attendance interval should not start before start_dt")
        self.assertTrue(end_dt >= result_per_resource_id[flex_resource.id]._items[4][1], "Last attendance interval should not end after end_dt")

    def test_public_holiday_calendar_no_company(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Holiday for company",
            'company_id': self.env.company.id,
            'date_from': datetime(2019, 5, 29, 0, 0, 0),
            'date_to': datetime(2019, 5, 30, 0, 0, 0),
            'resource_id': False,
            'time_type': "leave",
        }])
        calendar = self.env['resource.calendar'].create({
            'name': '40 hours/week',
            'hours_per_day': 8,
            'full_time_required_hours': 40,
        })
        calendar.company_id = False
        date_from = datetime(2019, 5, 27, 0, 0, 0).astimezone(UTC)
        date_to = datetime(2019, 5, 31, 23, 59, 59).astimezone(UTC)
        days = calendar._get_unusual_days(date_from, date_to, self.env.company)
        expected_res = {
            '2019-05-27': False,
            '2019-05-28': False,
            '2019-05-29': True,
            '2019-05-30': False,
            '2019-05-31': False,
        }
        self.assertEqual(days, expected_res)
