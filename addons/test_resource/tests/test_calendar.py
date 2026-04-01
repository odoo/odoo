from datetime import date, datetime

from pytz import timezone

from odoo import fields

from odoo.addons.test_resource.tests.common import TestResourceCommon


class TestCalendar(TestResourceCommon):
    def setUp(self):
        super().setUp()

    def test_get_work_hours_count(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'resource_id': False,
            'calendar_id': self.calendar_jean.id,
            'date_from': self.datetime_str(2018, 4, 3, 0, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 3, 23, 59, 59, tzinfo=self.jean.tz),
        })

        self.env['resource.calendar.leaves'].create({
            'name': 'leave for Jean',
            'calendar_id': self.calendar_jean.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2018, 4, 5, 0, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 5, 23, 59, 59, tzinfo=self.jean.tz),
        })

        hours = self.calendar_jean.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 59, 59, tzinfo=self.jean.tz),
        )
        self.assertEqual(hours, 32)

        hours = self.calendar_jean.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 4, 6, 23, 59, 59, tzinfo=self.jean.tz),
            compute_leaves=False,
        )
        self.assertEqual(hours, 40)

        # leave of size 0
        self.env['resource.calendar.leaves'].create({
            'name': 'zero_length',
            'calendar_id': self.calendar_patel.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 3, 0, 0, 0, tzinfo=self.patel.tz),
            'date_to': self.datetime_str(2018, 4, 3, 0, 0, 0, tzinfo=self.patel.tz),
        })

        hours = self.calendar_patel.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.tz),
        )
        self.assertEqual(hours, 35)

        # leave of medium size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero_length',
            'calendar_id': self.calendar_patel.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 3, 9, 0, 0, tzinfo=self.patel.tz),
            'date_to': self.datetime_str(2018, 4, 3, 12, 0, 0, tzinfo=self.patel.tz),
        })

        hours = self.calendar_patel.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.tz),
        )
        self.assertEqual(hours, 32)

        leave.unlink()

        # leave of very small size
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'zero_length',
            'calendar_id': self.calendar_patel.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 3, 0, 0, 0, tzinfo=self.patel.tz),
            'date_to': self.datetime_str(2018, 4, 3, 0, 0, 10, tzinfo=self.patel.tz),
        })

        hours = self.calendar_patel.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.tz),
        )
        self.assertEqual(hours, 35)

        leave.unlink()

        # no timezone given should be converted to UTC
        # Should equal to a leave between 2018/04/03 10:00:00 and 2018/04/04 10:00:00
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'no timezone',
            'calendar_id': self.calendar_patel.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 3, 4, 0, 0),
            'date_to': self.datetime_str(2018, 4, 4, 4, 0, 0),
        })

        hours = self.calendar_patel.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.tz),
        )
        self.assertEqual(hours, 28)

        hours = self.calendar_patel.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 23, 59, 59, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.tz),
        )
        self.assertEqual(hours, 0)

        leave.unlink()

        # 2 weeks calendar week 1
        hours = self.calendar_jules.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.jules.tz),
            self.datetime_tz(2018, 4, 6, 23, 59, 59, tzinfo=self.jules.tz),
        )
        self.assertEqual(hours, 30)

        # 2 weeks calendar week 1
        hours = self.calendar_jules.get_work_hours_count(
            self.datetime_tz(2018, 4, 16, 0, 0, 0, tzinfo=self.jules.tz),
            self.datetime_tz(2018, 4, 20, 23, 59, 59, tzinfo=self.jules.tz),
        )
        self.assertEqual(hours, 30)

        # 2 weeks calendar week 2
        hours = self.calendar_jules.get_work_hours_count(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.jules.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.jules.tz),
        )
        self.assertEqual(hours, 16)

        # 2 weeks calendar week 2, leave during a day where he doesn't work this week
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'Time Off Jules week 2',
            'calendar_id': self.calendar_jules.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 11, 4, 0, 0, tzinfo=self.jules.tz),
            'date_to': self.datetime_str(2018, 4, 13, 4, 0, 0, tzinfo=self.jules.tz),
        })

        hours = self.calendar_jules.get_work_hours_count(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.jules.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.jules.tz),
        )
        self.assertEqual(hours, 16)

        leave.unlink()

        # 2 weeks calendar week 2, leave during a day where he works this week
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'Time Off Jules week 2',
            'calendar_id': self.calendar_jules.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 9, 0, 0, 0, tzinfo=self.jules.tz),
            'date_to': self.datetime_str(2018, 4, 9, 23, 59, 0, tzinfo=self.jules.tz),
        })

        hours = self.calendar_jules.get_work_hours_count(
            self.datetime_tz(2018, 4, 9, 0, 0, 0, tzinfo=self.jules.tz),
            self.datetime_tz(2018, 4, 13, 23, 59, 59, tzinfo=self.jules.tz),
        )
        self.assertEqual(hours, 8)

        leave.unlink()

        # leave without calendar, should count for anyone in the company
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'small leave',
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 3, 9, 0, 0, tzinfo=self.patel.tz),
            'date_to': self.datetime_str(2018, 4, 3, 12, 0, 0, tzinfo=self.patel.tz),
        })

        hours = self.calendar_patel.get_work_hours_count(
            self.datetime_tz(2018, 4, 2, 0, 0, 0, tzinfo=self.patel.tz),
            self.datetime_tz(2018, 4, 6, 23, 59, 59, tzinfo=self.patel.tz),
        )
        self.assertEqual(hours, 32)

    def test_calendar_working_hours_count(self):
        calendar = self.env['resource.calendar'].create({
            'name': 'Standard 35 hours/week',
            'company_id': self.env.company.id,
            'tz': 'UTC',
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
            ],
        })
        res = calendar.get_work_hours_count(
            fields.Datetime.from_string('2017-05-03 14:03:00'),  # Wednesday (8:00-12:00, 13:00-16:00)
            fields.Datetime.from_string('2017-05-04 11:03:00'),  # Thursday (8:00-12:00, 13:00-16:00)
            compute_leaves=False)
        self.assertEqual(res, 5.0)

    def test_calendar_working_hours_24(self):
        self.att_4 = self.env['resource.calendar.attendance'].create({
            'name': 'Att4',
            'calendar_id': self.calendar_jean.id,
            'dayofweek': '2',
            'hour_from': 0,
            'hour_to': 24,
        })
        res = self.calendar_jean.get_work_hours_count(
            self.datetime_tz(2018, 6, 19, 23, 0, 0, tzinfo=self.jean.tz),
            self.datetime_tz(2018, 6, 21, 1, 0, 0, tzinfo=self.jean.tz),
            compute_leaves=True)
        self.assertAlmostEqual(res, 24.0)

    def test_plan_hours(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'global',
            'calendar_id': self.calendar_jean.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 11, 0, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 11, 23, 59, 59, tzinfo=self.jean.tz),
        })

        time = self.calendar_jean.plan_hours(2, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=False)
        self.assertEqual(time, self.datetime_tz(2018, 4, 10, 10, 0, 0, tzinfo=self.jean.tz))

        time = self.calendar_jean.plan_hours(20, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=False)
        self.assertEqual(time, self.datetime_tz(2018, 4, 12, 12, 0, 0, tzinfo=self.jean.tz))

        time = self.calendar_jean.plan_hours(5, self.datetime_tz(2018, 4, 10, 15, 0, 0, tzinfo=self.jean.tz), compute_leaves=True)
        self.assertEqual(time, self.datetime_tz(2018, 4, 12, 12, 0, 0, tzinfo=self.jean.tz))

        # negative planning
        time = self.calendar_jean.plan_hours(-10, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=True)
        self.assertEqual(time, self.datetime_tz(2018, 4, 6, 14, 0, 0, tzinfo=self.jean.tz))

        # zero planning with holidays
        time = self.calendar_jean.plan_hours(0, self.datetime_tz(2018, 4, 11, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=True)
        self.assertEqual(time, self.datetime_tz(2018, 4, 12, 8, 0, 0, tzinfo=self.jean.tz))
        time = self.calendar_jean.plan_hours(0, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=False)
        self.assertEqual(time, self.datetime_tz(2018, 4, 10, 8, 0, 0, tzinfo=self.jean.tz))

        # very small planning
        time = self.calendar_jean.plan_hours(0.0002, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=True)
        self.assertEqual(time, self.datetime_tz(2018, 4, 10, 8, 0, 0, 720000, tzinfo=self.jean.tz))

        # huge planning
        time = self.calendar_jean.plan_hours(3000, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=False)
        self.assertEqual(time, self.datetime_tz(2019, 9, 16, 16, 0, 0, tzinfo=self.jean.tz))

    def test_plan_days(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'global',
            'calendar_id': self.calendar_jean.id,
            'resource_id': False,
            'date_from': self.datetime_str(2018, 4, 11, 0, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2018, 4, 11, 23, 59, 59, tzinfo=self.jean.tz),
        })

        time = self.calendar_jean.plan_days(1, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=False)
        self.assertEqual(time, self.datetime_tz(2018, 4, 10, 16, 0, 0, tzinfo=self.jean.tz))

        time = self.calendar_jean.plan_days(3, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=False)
        self.assertEqual(time, self.datetime_tz(2018, 4, 12, 16, 0, 0, tzinfo=self.jean.tz))

        time = self.calendar_jean.plan_days(4, self.datetime_tz(2018, 4, 10, 16, 0, 0, tzinfo=self.jean.tz), compute_leaves=True)
        self.assertEqual(time, self.datetime_tz(2018, 4, 17, 16, 0, 0, tzinfo=self.jean.tz))

        # negative planning
        time = self.calendar_jean.plan_days(-10, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=True)
        self.assertEqual(time, self.datetime_tz(2018, 3, 27, 8, 0, 0, tzinfo=self.jean.tz))

        # zero planning
        time = self.calendar_jean.plan_days(0, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=True)
        self.assertEqual(time, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz))

        # very small planning returns False in this case
        # TODO: decide if this behaviour is alright
        time = self.calendar_jean.plan_days(0.0002, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=True)
        self.assertEqual(time, False)

        # huge planning
        # TODO: Same as above
        # NOTE: Maybe allow to set a max limit to the method
        time = self.calendar_jean.plan_days(3000, self.datetime_tz(2018, 4, 10, 0, 0, 0, tzinfo=self.jean.tz), compute_leaves=False)
        self.assertEqual(time, False)

    def test_closest_time(self):
        # Calendar:
        # Tuesdays 8-16
        # Fridays 8-13 and 16-23
        dt = self.datetime_tz(2020, 4, 2, 7, 0, 0, tzinfo=self.john.tz)
        calendar_dt = self.calendar_john._get_closest_work_time(dt)
        self.assertFalse(calendar_dt, "It should not return any value for unattended days")

        dt = self.datetime_tz(2020, 4, 3, 7, 0, 0, tzinfo=self.john.tz)
        range_start = self.datetime_tz(2020, 4, 3, 8, 0, 0, tzinfo=self.john.tz)
        range_end = self.datetime_tz(2020, 4, 3, 19, 0, 0, tzinfo=self.john.tz)
        calendar_dt = self.calendar_john._get_closest_work_time(dt, search_range=(range_start, range_end))
        self.assertFalse(calendar_dt, "It should not return any value if dt outside of range")

        dt = self.datetime_tz(2020, 4, 3, 7, 0, 0, tzinfo=self.john.tz)  # before
        start = self.datetime_tz(2020, 4, 3, 8, 0, 0, tzinfo=self.john.tz)
        calendar_dt = self.calendar_john._get_closest_work_time(dt)
        self.assertEqual(calendar_dt, start, "It should return the start of the day")

        dt = self.datetime_tz(2020, 4, 3, 10, 0, 0, tzinfo=self.john.tz)  # after
        start = self.datetime_tz(2020, 4, 3, 8, 0, 0, tzinfo=self.john.tz)
        calendar_dt = self.calendar_john._get_closest_work_time(dt)
        self.assertEqual(calendar_dt, start, "It should return the start of the closest attendance")

        dt = self.datetime_tz(2020, 4, 3, 7, 0, 0, tzinfo=self.john.tz)  # before
        end = self.datetime_tz(2020, 4, 3, 13, 0, 0, tzinfo=self.john.tz)
        calendar_dt = self.calendar_john._get_closest_work_time(dt, match_end=True)
        self.assertEqual(calendar_dt, end, "It should return the end of the closest attendance")

        dt = self.datetime_tz(2020, 4, 3, 14, 0, 0, tzinfo=self.john.tz)  # after
        end = self.datetime_tz(2020, 4, 3, 13, 0, 0, tzinfo=self.john.tz)
        calendar_dt = self.calendar_john._get_closest_work_time(dt, match_end=True)
        self.assertEqual(calendar_dt, end, "It should return the end of the closest attendance")

        dt = self.datetime_tz(2020, 4, 3, 0, 0, 0, tzinfo=self.john.tz)
        start = self.datetime_tz(2020, 4, 3, 8, 0, 0, tzinfo=self.john.tz)
        calendar_dt = self.calendar_john._get_closest_work_time(dt)
        self.assertEqual(calendar_dt, start, "It should return the start of the closest attendance")

        dt = self.datetime_tz(2020, 4, 3, 23, 59, 59, tzinfo=self.john.tz)
        end = self.datetime_tz(2020, 4, 3, 23, 0, 0, tzinfo=self.john.tz)
        calendar_dt = self.calendar_john._get_closest_work_time(dt, match_end=True)
        self.assertEqual(calendar_dt, end, "It should return the end of the closest attendance")

    def test_attendance_interval_edge_tz(self):
        # When genereting the attendance intervals in an edge timezone, the last interval shouldn't
        # be truncated if the timezone is correctly set
        self.env.user.tz = "America/Los_Angeles"
        self.calendar_jean.tz = "America/Los_Angeles"
        attendances = self.calendar_jean._attendance_intervals_batch(
            datetime.combine(date(2023, 1, 1), datetime.min.time(), tzinfo=timezone("UTC")),
            datetime.combine(date(2023, 1, 31), datetime.max.time(), tzinfo=timezone("UTC")))
        last_attendance = list(attendances[False])[-1]
        self.assertEqual(last_attendance[0].replace(tzinfo=None), datetime(2023, 1, 31, 8))
        self.assertEqual(last_attendance[1].replace(tzinfo=None), datetime(2023, 1, 31, 15, 59, 59, 999999))

        attendances = self.calendar_jean._attendance_intervals_batch(
            datetime.combine(date(2023, 1, 1), datetime.min.time(), tzinfo=timezone("America/Los_Angeles")),
            datetime.combine(date(2023, 1, 31), datetime.max.time(), tzinfo=timezone("America/Los_Angeles")))
        last_attendance = list(attendances[False])[-1]
        self.assertEqual(last_attendance[0].replace(tzinfo=None), datetime(2023, 1, 31, 8))
        self.assertEqual(last_attendance[1].replace(tzinfo=None), datetime(2023, 1, 31, 16))

    def test_resource_calendar_update(self):
        """ Ensure leave calendar gets set correctly when updating resource calendar. """
        holiday = self.env['resource.calendar.leaves'].create({
            'name': "May Day",
            'calendar_id': self.calendar_jean.id,
            'date_from': self.datetime_str(2024, 5, 1, 0, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2024, 5, 1, 23, 59, 59, tzinfo=self.jean.tz),
        })

        # Jean takes a leave
        leave = self.env['resource.calendar.leaves'].create({
            'name': "Jean is AFK",
            'calendar_id': self.calendar_jean.id,
            'resource_id': self.jean.resource_id.id,
            'date_from': self.datetime_str(2024, 5, 10, 8, 0, 0, tzinfo=self.jean.tz),
            'date_to': self.datetime_str(2024, 5, 10, 16, 0, 0, tzinfo=self.jean.tz),
        })

        # Jean changes working schedule to Jules'
        self.jean.resource_calendar_id = self.calendar_jules
        self.assertEqual(leave.calendar_id, self.calendar_jules, "Leave calendar should update")
        self.assertEqual(holiday.calendar_id, self.calendar_jean, "Global leave shouldn't change")

    def test_compute_work_time_rate_with_one_week_calendar(self):
        """Test Case: check if the computation of the work time rate in the resource.calendar is correct."""
        # Define a mid time
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Calendar Mid-Time',
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'full_time_required_hours': 40,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ],
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 50, 2)

        # Define a 4/5
        resource_calendar.write({
            'name': 'Calendar (4 / 5)',
            'attendance_ids': [
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 80, 2)

        # Define a 9/10
        resource_calendar.write({
            'name': 'Calendar (9 / 10)',
            'attendance_ids': [(0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})],
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 90, 2)

        # Define a Full-Time
        resource_calendar.write({
            'name': 'Calendar Full-Time',
            'attendance_ids': [(0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})],
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 100, 2)

    def test_compute_work_time_rate_with_two_weeks_calendar(self):
        """Test Case: check if the computation of the work time rate in the resource.calendar is correct."""
        def create_attendance_ids(attendance_list):
            return [(0, 0, {'week_type': str(i), **attendance}) for i in range(0, 2) for attendance in attendance_list]

        attendance_list = [
            {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'},
            {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'},
            {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
        ]

        # Define a mid time
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Calendar Mid-Time',
            'tz': "Europe/Brussels",
            'two_weeks_calendar': True,
            'full_time_required_hours': 40,
            'attendance_ids': create_attendance_ids(attendance_list),
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 50, 2)

        attendance_list = [
            {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
            {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'},
            {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'},
            {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'},
        ]

        # Define a 4/5
        resource_calendar.write({
            'name': 'Calendar (4 / 5)',
            'attendance_ids': create_attendance_ids(attendance_list),
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 80, 2)

        # Define a 9/10
        resource_calendar.write({
            'name': 'Calendar (9 / 10)',
            'attendance_ids': create_attendance_ids([{'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}]),
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 90, 2)

        # Define a Full-Time
        resource_calendar.write({
            'name': 'Calendar Full-Time',
            'attendance_ids': create_attendance_ids([{'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}]),
        })
        self.assertAlmostEqual(resource_calendar.work_time_rate, 100, 2)
