# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command
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
