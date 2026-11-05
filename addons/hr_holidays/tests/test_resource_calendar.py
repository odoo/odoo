# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command
from odoo.exceptions import ValidationError
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

        # Monday (pm start) -> Wednesday (am end): Monday and Wednesday are half days,
        # Tuesday in between is a full day.
        leave_partial = self.env['hr.leave'].create({
            'name': 'Half day Monday to half day Wednesday',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2026, 4, 27),
            'request_date_to': date(2026, 4, 29),
            'request_date_from_period': 'pm',
            'request_date_to_period': 'am',
        })
        self.assertEqual(leave_partial.number_of_days, 2)
        self.assertEqual(leave_partial.number_of_hours, 13.44)

        # Sunday -> Monday: Sunday is not worked, only Monday should be counted.
        leave_non_working_start = self.env['hr.leave'].create({
            'name': 'Sunday to Monday',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date(2026, 10, 11),
            'request_date_to': date(2026, 10, 12),
            'request_date_from_period': 'am',
            'request_date_to_period': 'pm',
        })
        self.assertEqual(leave_non_working_start.number_of_days, 1)
        self.assertEqual(leave_non_working_start.number_of_hours, 6.72)

    def test_time_off_duration_based_calendar_day_hours(self):
        """ The time off taken on a day can't exceed the hours of the day with time off in hours """
        # 4 hours in the morning and 3 hours in the afternoon
        self.calendar_35h.duration_based = True
        leave_type_hour = self.env['hr.leave.type'].create({
            'name': 'Test hour type',
            'requires_allocation': False,
            'request_unit': 'hour',
        })
        monday_vals = {
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type_hour.id,
            'request_date_from': date(2026, 4, 20),
            'request_date_to': date(2026, 4, 20),
        }

        # 4 + 3 hours fit in the 7 hours of the day, not 1 more
        morning_leave, _afternoon_leave = self.env['hr.leave'].create([
            {**monday_vals, 'request_hour_from': 8, 'request_hour_to': 12},
            {**monday_vals, 'request_hour_from': 13, 'request_hour_to': 16},
        ])
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].create({**monday_vals, 'request_hour_from': 18, 'request_hour_to': 19})

        # Once a time off is refused, its hours can be taken again
        morning_leave.action_refuse()
        leave = self.env['hr.leave'].create({**monday_vals, 'request_hour_from': 18, 'request_hour_to': 22})
        self.assertEqual(leave.number_of_hours, 4)

        # A full day leaves no hour for time off in hours outside of its hours
        tuesday_vals = {**monday_vals, 'request_date_from': date(2026, 4, 21), 'request_date_to': date(2026, 4, 21)}
        self.env['hr.leave'].create({**tuesday_vals, 'holiday_status_id': self.leave_type.id})
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].create({**tuesday_vals, 'request_hour_from': 18, 'request_hour_to': 20})
