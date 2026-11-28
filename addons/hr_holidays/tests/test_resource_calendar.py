# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo import Command
from odoo.tests import Form
from odoo.tests.common import tagged

from odoo.addons.hr_holidays.tests.common import TestHolidayContract


@tagged('post_install', '-at_install')
class TestResourceCalendar(TestHolidayContract):

    def test_time_off_half_day_duration(self):
        """if working schedule is of full day period, Duration should be correct"""

        new_calendar_40h = self.env['resource.calendar'].create({
            'name': '40h calendar new',
            'attendance_ids': [
                Command.create({
                    'name': 'Monday full day',
                    'dayofweek': '0',
                    'hour_from': 10,
                    'hour_to': 18,
                    'day_period': 'full_day',
                }),
                Command.create({
                    'name': 'Tuesday full day',
                    'dayofweek': '1',
                    'hour_from': 10,
                    'hour_to': 18,
                    'day_period': 'full_day',
                }),
            ],
        })
        self.jules_emp.version_id.resource_calendar_id = new_calendar_40h.id
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test half day type',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'request_unit': 'half_day',
        })

        leave_morning, leave_afternoon, leave_one_and_half = self.env['hr.leave'].create([
            {
                'name': 'Half Day Leave(morning)',
                'employee_id': self.jules_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date(2025, 4, 21),
                'request_date_to': date(2025, 4, 21),
                'request_date_from_period': 'am',
                'request_date_to_period': 'am',
            },
            {
                'name': 'Half Day Leave(afternoon)',
                'employee_id': self.jules_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date(2025, 4, 22),
                'request_date_to': date(2025, 4, 22),
                'request_date_from_period': 'pm',
                'request_date_to_period': 'pm',
            },
            {
                'name': 'One and half Day Leave',
                'employee_id': self.jules_emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date(2025, 4, 14),
                'request_date_to': date(2025, 4, 15),
                'request_date_from_period': 'am',
                'request_date_to_period': 'am',
            },
        ])
        self.assertEqual(leave_morning.number_of_days, 0.5)
        self.assertEqual(leave_afternoon.number_of_days, 0.5)
        self.assertEqual(leave_one_and_half.number_of_days, 1.5)

    def test_time_off_half_day_duration_based_calendar(self):
        attendance_ids = []
        for dayofweek, day_name in [
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
        ]:
            attendance_ids += [
                Command.create({
                    'name': f'{day_name} Morning',
                    'dayofweek': dayofweek,
                    'duration_hours': 3.36,
                    'day_period': 'morning',
                }),
                Command.create({
                    'name': f'{day_name} Afternoon',
                    'dayofweek': dayofweek,
                    'duration_hours': 3.36,
                    'day_period': 'afternoon',
                }),
            ]

        calendar = self.env['resource.calendar'].create({
            'name': 'Duration based calendar',
            'duration_based': True,
            'attendance_ids': attendance_ids,
        })
        self.jules_emp.version_id.resource_calendar_id = calendar
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test duration based half day type',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'request_unit': 'half_day',
        })

        leave = self.env['hr.leave'].create({
            'name': 'Full week half day leave',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2026, 4, 20),
            'request_date_to': date(2026, 4, 24),
            'request_date_from_period': 'am',
            'request_date_to_period': 'pm',
        })

        self.assertEqual(leave.number_of_days, 5)

    def _create_hour_leave_type(self, leave_validation_type='no_validation', time_type='leave'):
        return self.env['hr.leave.type'].create({
            'name': 'Custom hours type',
            'time_type': time_type,
            'requires_allocation': False,
            'leave_validation_type': leave_validation_type,
            'request_unit': 'hour',
        })

    def _create_duration_based_calendar(self, hours_per_weekday=None):
        """Duration based calendar without real start/end times: each attendance
        is only a duration, stored as a window centered on 12:00 (8h => 08:00-16:00).
        """
        hours_per_weekday = hours_per_weekday or {'0': 8, '1': 8, '2': 8, '3': 8, '4': 8}
        # the resource timezone is the one used to place the requested hours
        self.jules_emp.tz = 'Europe/Brussels'
        return self.env['resource.calendar'].create({
            'name': 'Duration based calendar',
            'tz': 'Europe/Brussels',
            'duration_based': True,
            'attendance_ids': [
                Command.create({
                    'name': f'Day {dayofweek}',
                    'dayofweek': dayofweek,
                    'duration_hours': duration,
                    'day_period': 'full_day',
                }) for dayofweek, duration in hours_per_weekday.items()
            ],
        })

    def _create_hour_leave(self, leave_type, date_from, date_to, hour_from, hour_to):
        return self.env['hr.leave'].create({
            'name': 'Custom hours leave',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
            'request_hour_from': hour_from,
            'request_hour_to': hour_to,
        })

    def test_custom_hours_duration_based_calendar_counts_requested_length(self):
        """On a schedule without start/end times, a custom hours request counts
        its real length (capped at the hours of the day), not the overlap with
        the 08:00-16:00 window the duration is stored as."""
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar()
        leave_type = self._create_hour_leave_type()

        for week, (hour_from, hour_to, expected_hours) in enumerate([
            (12, 16, 4),
            (12, 15, 3),
            (12, 17, 5),
            (7, 17, 8),  # capped at the hours of the day
            (6, 10, 4),
            (8, 16, 8),
        ]):
            with self.subTest(hour_from=hour_from, hour_to=hour_to):
                # one week apart to avoid overlapping requests
                monday = date(2026, 4, 20) + timedelta(weeks=week)
                leave = self._create_hour_leave(leave_type, monday, monday, hour_from, hour_to)
                self.assertAlmostEqual(leave.number_of_hours, expected_hours)
                # days must stay consistent with the hours
                self.assertAlmostEqual(leave.number_of_days, expected_hours / 8, places=2)
                self.assertEqual(leave.duration_display, f"{expected_hours}:00 hours")

    def test_custom_hours_duration_based_calendar_non_working_day(self):
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar()
        saturday = date(2026, 4, 25)
        # needs an approval: an approved request on a non working day is refused
        leave_type = self._create_hour_leave_type(leave_validation_type='hr')
        leave = self._create_hour_leave(leave_type, saturday, saturday, 10, 14)
        self.assertEqual(leave.number_of_hours, 0)
        self.assertEqual(leave.number_of_days, 0)

    def test_custom_hours_duration_based_calendar_public_holiday(self):
        """The hours overlapping a public holiday are not counted."""
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar()
        monday = date(2026, 4, 20)
        # 13:00 -> 15:00 Brussels (UTC+2)
        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'company_id': self.jules_emp.company_id.id,
            'date_from': datetime(2026, 4, 20, 11, 0),
            'date_to': datetime(2026, 4, 20, 13, 0),
        })
        leave = self._create_hour_leave(self._create_hour_leave_type(), monday, monday, 12, 17)
        self.assertAlmostEqual(leave.number_of_hours, 3)
        self.assertAlmostEqual(leave.number_of_days, 3 / 8, places=2)

    def test_custom_hours_duration_based_calendar_multiple_days(self):
        """The hours are capped per day, using the hours of each weekday."""
        # Monday: 8h, Tuesday: 4h
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar({'0': 8, '1': 4})
        leave_type = self._create_hour_leave_type()
        monday, tuesday = date(2026, 4, 20), date(2026, 4, 21)

        leave = self._create_hour_leave(leave_type, monday, tuesday, 12, 17)
        # Monday from 12:00 on (12h, capped to 8h) + Tuesday until 17:00 (17h, capped to 4h)
        self.assertAlmostEqual(leave.number_of_hours, 12)
        self.assertAlmostEqual(leave.number_of_days, 2)

        next_tuesday = tuesday + timedelta(weeks=1)
        tuesday_leave = self._create_hour_leave(leave_type, next_tuesday, next_tuesday, 12, 17)
        self.assertAlmostEqual(tuesday_leave.number_of_hours, 4)
        self.assertAlmostEqual(tuesday_leave.number_of_days, 1)

    def test_custom_hours_duration_based_calendar_multiple_days_partial_edges(self):
        """The hour from applies to the first day only, the hour to to the last day only,
        and the days in between count in full."""
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar()
        monday, wednesday = date(2026, 4, 20), date(2026, 4, 22)

        # Monday from 18:00 (6h), Tuesday in full (8h), Wednesday until 03:00 (3h)
        leave = self._create_hour_leave(self._create_hour_leave_type(), monday, wednesday, 18, 3)
        self.assertAlmostEqual(leave.number_of_hours, 17)
        self.assertAlmostEqual(leave.number_of_days, 6 / 8 + 1 + 3 / 8, places=2)

    def test_custom_hours_duration_based_calendar_worked_time_is_capped_too(self):
        """A worked time request is capped at the hours of the day, like an absence."""
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar()
        monday, next_monday = date(2026, 4, 20), date(2026, 4, 27)

        for day, time_type in [(monday, 'other'), (next_monday, 'leave')]:
            with self.subTest(time_type=time_type):
                leave = self._create_hour_leave(
                    self._create_hour_leave_type(time_type=time_type), day, day, 6, 18)
                self.assertAlmostEqual(leave.number_of_hours, 8)
                self.assertAlmostEqual(leave.number_of_days, 1)

        saturday = date(2026, 4, 25)
        # needs an approval: an approved request on a non working day is refused
        worked_time = self._create_hour_leave(
            self._create_hour_leave_type(leave_validation_type='hr', time_type='other'),
            saturday, saturday, 10, 14)
        self.assertEqual(worked_time.number_of_hours, 0)
        self.assertEqual(worked_time.number_of_days, 0)

    def test_custom_hours_duration_based_calendar_cap_counts_other_leaves_of_the_day(self):
        """Several absences of the same day can't add up to more than the hours of that day."""
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar()
        leave_type = self._create_hour_leave_type()
        monday = date(2026, 4, 20)

        first = self._create_hour_leave(leave_type, monday, monday, 8, 10)
        second = self._create_hour_leave(leave_type, monday, monday, 12, 20)
        self.assertAlmostEqual(first.number_of_hours, 2)
        self.assertAlmostEqual(second.number_of_hours, 6)
        self.assertAlmostEqual(second.number_of_days, 6 / 8, places=2)

    def test_custom_hours_duration_based_calendar_cap_counts_public_holiday_of_the_day(self):
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar()
        monday = date(2026, 4, 20)
        # 12:00 -> 13:00 Brussels (UTC+2)
        self.env['resource.calendar.leaves'].create({
            'name': 'Public holiday',
            'company_id': self.jules_emp.company_id.id,
            'date_from': datetime(2026, 4, 20, 10, 0),
            'date_to': datetime(2026, 4, 20, 11, 0),
        })
        leave = self._create_hour_leave(self._create_hour_leave_type(), monday, monday, 7, 17)
        # 10h requested - 1h of public holiday = 9h, but only 8h - 1h = 7h are left for that day
        self.assertAlmostEqual(leave.number_of_hours, 7)

    def test_custom_hours_calendar_with_real_hours_keeps_overlap(self):
        """With real start/end times, only the overlap with the working hours counts."""
        calendar = self.env['resource.calendar'].create({
            'name': 'Real hours calendar',
            'tz': 'Europe/Brussels',
            'attendance_ids': [
                Command.create({
                    'name': 'Monday',
                    'dayofweek': '0',
                    'hour_from': 8,
                    'hour_to': 16,
                    'day_period': 'full_day',
                }),
            ],
        })
        self.jules_emp.version_id.resource_calendar_id = calendar
        monday = date(2026, 4, 20)
        leave = self._create_hour_leave(self._create_hour_leave_type(), monday, monday, 12, 17)
        self.assertAlmostEqual(leave.number_of_hours, 4)

    def test_custom_hours_duration_display_follows_hours_in_form(self):
        self.jules_emp.version_id.resource_calendar_id = self._create_duration_based_calendar()
        monday = date(2026, 4, 20)
        with Form(self.env['hr.leave']) as leave_form:
            leave_form.employee_id = self.jules_emp
            leave_form.holiday_status_id = self._create_hour_leave_type()
            leave_form.request_date_from = monday
            leave_form.request_date_to = monday
            leave_form.request_hour_from = 12
            leave_form.request_hour_to = 17
            self.assertEqual(leave_form.duration_display, "5:00 hours")
            leave_form.request_hour_to = 14
            self.assertEqual(leave_form.duration_display, "2:00 hours")
            leave_form.request_hour_from = 6
            self.assertEqual(leave_form.duration_display, "8:00 hours")
