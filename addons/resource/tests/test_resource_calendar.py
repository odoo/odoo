# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pytz
from datetime import datetime

from odoo.tests import Form, TransactionCase


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
        date_from = datetime(2019, 5, 27, 0, 0, 0).astimezone(pytz.UTC)
        date_to = datetime(2019, 5, 31, 23, 59, 59).astimezone(pytz.UTC)
        days = calendar._get_unusual_days(date_from, date_to, self.env.company)
        expected_res = {
            '2019-05-27': False,
            '2019-05-28': False,
            '2019-05-29': True,
            '2019-05-30': False,
            '2019-05-31': False,
        }
        self.assertEqual(days, expected_res)

    def test_company_change_attendance_persistence(self):
        """
        Test to ensure that altering the company does not wipe the current schedule.
        """
        work_schedule = self.env['resource.calendar'].create({
            'name': 'Test Work Schedule',
            'company_id': False,
            'attendance_ids': False
        })
        attendance_1 = self.env['resource.calendar.attendance'].create({
            'name': 'Attendance 1',
            'calendar_id': work_schedule.id,
            'dayofweek': '1',
            'hour_from': 8,
            'hour_to': 17,
        })
        self.env.user.groups_id += self.env.ref('base.group_multi_company')
        with Form(work_schedule) as form:
            form.company_id = self.env.company

        self.assertEqual(work_schedule.attendance_ids, attendance_1)

    def test_flexible_calendar_attendance_intervals_with_leaves(self):
        flexible_calendar = self.env["resource.calendar"].create({
            "name": "Test Flexible Calendar",
            "flexible_hours": True,
            "full_time_required_hours": 40,
            "hours_per_day": 8,
            "tz": "UTC",
        })
        resource = self.env["resource.resource"].create({
            "name": "Test Resource",
            "calendar_id": flexible_calendar.id,
            "tz": "UTC",
        })
        self.env["resource.calendar.leaves"].create([
            {
                "name": "Late leave",
                "resource_id": resource.id,
                "date_from": datetime(2022, 1, 10, 16, 0),
                "date_to": datetime(2022, 1, 10, 17, 0),
            },
            {
                "name": "Early leave",
                "resource_id": resource.id,
                "date_from": datetime(2022, 1, 11, 10, 0),
                "date_to": datetime(2022, 1, 11, 11, 0),
            },
            {
                "name": "First hourly leave",
                "resource_id": resource.id,
                "date_from": datetime(2022, 1, 12, 10, 0),
                "date_to": datetime(2022, 1, 12, 11, 0),
            },
            {
                "name": "Second hourly leave",
                "resource_id": resource.id,
                "date_from": datetime(2022, 1, 12, 16, 0),
                "date_to": datetime(2022, 1, 12, 17, 0),
            },
            {
                "name": "Full-day leave",
                "resource_id": resource.id,
                "date_from": datetime(2022, 1, 14, 0, 0),
                "date_to": datetime(2022, 1, 14, 23, 59, 59),
            },
        ])

        start_dt = pytz.UTC.localize(datetime(2022, 1, 10))
        end_dt = pytz.UTC.localize(datetime(2022, 1, 14))
        work_intervals = flexible_calendar._work_intervals_batch(start_dt, end_dt, resources=resource)

        def get_ranges(intervals, day):
            return [
                (start.strftime("%H:%M"), stop.strftime("%H:%M"))
                for start, stop, _records in intervals[resource.id]
                if start.date() == day
            ]

        # 10 January: 16:00-17:00.
        # The synthetic attendance must end at 17:00.
        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 10).date()),
            [("09:00", "16:00")],
        )
        # 11 January: 10:00-11:00.
        # The default end-based calculation would start too early,
        # so use the leave start as reference.
        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 11).date()),
            [("11:00", "18:00")],
        )
        # 12 January: two separate hourly leaves.
        # Use the latest leave end as reference.
        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 12).date()),
            [("09:00", "10:00"), ("11:00", "16:00")],
        )
        # 13 January: no leaves, preserve the default behavior.
        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 13).date()),
            [("08:00", "16:00")],
        )
        # 14 January: a full-day leave already covers the default interval.
        # There is no reason to move it.
        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 14).date()),
            [],
        )

    def test_flexible_calendar_attendance_intervals_with_multi_day_leave(self):
        flexible_calendar = self.env["resource.calendar"].create({
            "name": "Test Flexible Calendar",
            "flexible_hours": True,
            "full_time_required_hours": 40,
            "hours_per_day": 8,
            "tz": "UTC",
        })
        resource = self.env["resource.resource"].create({
            "name": "Test Resource",
            "calendar_id": flexible_calendar.id,
            "tz": "UTC",
        })
        self.env["resource.calendar.leaves"].create({
            "name": "Multi-day leave",
            "resource_id": resource.id,
            "date_from": datetime(2022, 1, 10, 10, 0),
            "date_to": datetime(2022, 1, 12, 11, 0),
        })
        start_dt = pytz.UTC.localize(datetime(2022, 1, 10))
        end_dt = pytz.UTC.localize(datetime(2022, 1, 14))
        work_intervals = flexible_calendar._work_intervals_batch(start_dt, end_dt, resources=resource)

        def get_ranges(intervals, day):
            return [
                (start.strftime("%H:%M"), stop.strftime("%H:%M"))
                for start, stop, _records in intervals[resource.id]
                if start.date() == day
            ]

        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 10).date()),
            [],
        )
        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 11).date()),
            [],
        )
        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 12).date()),
            [],
        )
        self.assertEqual(
            get_ranges(work_intervals, datetime(2022, 1, 13).date()),
            [("08:00", "16:00")],
        )
