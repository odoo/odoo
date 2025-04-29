# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import ValidationError
from freezegun import freeze_time

from odoo.tests import tagged

@tagged('global_leaves')
class TestGlobalLeaves(TestHrHolidaysCommon):
    """ Test global leaves for a whole company, conflict resolutions """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_1 = cls.env['resource.calendar'].create({
            'name': 'Classic 40h/week',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ]
        })

        cls.calendar_2 = cls.env['resource.calendar'].create({
            'name': 'Classic 20h/week',
            'tz': 'UTC',
            'hours_per_day': 4.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ]
        })

        cls.global_leave = cls.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': date(2022, 3, 7),
            'date_to': date(2022, 3, 7),
        })

        cls.calendar_leave = cls.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': date(2022, 3, 8),
            'date_to': date(2022, 3, 8),
            'calendar_id': cls.calendar_1.id,
        })

    def test_leave_on_global_leave(self):
        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Time Off',
                'date_from': date(2022, 3, 7),
                'date_to': date(2022, 3, 7),
                'calendar_id': self.calendar_1.id,
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Time Off',
                'date_from': date(2022, 3, 7),
                'date_to': date(2022, 3, 7),
            })

    def test_leave_on_calendar_leave(self):
        self.env['resource.calendar.leaves'].create({
                'name': 'Correct Time Off',
                'date_from': date(2022, 3, 8),
                'date_to': date(2022, 3, 8),
                'calendar_id': self.calendar_2.id,
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Time Off',
                'date_from': date(2022, 3, 8),
                'date_to': date(2022, 3, 8),
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Time Off',
                'date_from': date(2022, 3, 8),
                'date_to': date(2022, 3, 8),
                'calendar_id': self.calendar_1.id,
            })

    @freeze_time('2023-05-12')
    def test_global_leave_timezone(self):
        """
            It is necessary to use the timezone of the calendar
            for the global leaves (without resource).
        """
        calendar_asia = self.env['resource.calendar'].create({
            'name': 'Asia calendar',
            'tz': 'Asia/Kolkata', # UTC +05:30
            'hours_per_day': 8.0,
            'attendance_ids': []
        })
        self.env.user.tz = 'Europe/Brussels'
        global_leave = self.env['resource.calendar.leaves'].with_user(self.env.user).create({
            'name': 'Public holiday',
            'date_from': "2023-05-15 06:00:00", # utc from 8:00:00 for Europe/Brussels (UTC +02:00)
            'date_to': "2023-05-15 15:00:00", # utc from 17:00:00 for Europe/Brussels (UTC +02:00)
            'calendar_id': calendar_asia.id,
        })
        # Expectation:
        # 6:00:00 in UTC (data from the browser) --> 8:00:00 for Europe/Brussel (UTC +02:00)
        # 8:00:00 for Asia/Kolkata (UTC +05:30) --> 2:30:00 in UTC
        self.assertEqual(global_leave.date_from, datetime(2023, 5, 15, 2, 30))
        self.assertEqual(global_leave.date_to, datetime(2023, 5, 15, 11, 30))
        # Note:
        # The user in Europe/Brussels timezone see 4:30 and not 2:30 because he is in UTC +02:00.
        # The user in Asia/Kolkata timezone (determined via the browser) see 8:00 because he is in UTC +05:30

    def test_global_leave_number_of_days_with_new(self):
        """
            Check that leaves stored in memory (and not in the database)
            take into account global leaves.
        """
        global_leave = self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': datetime(2024, 1, 3, 6, 0, 0),
            'date_to': datetime(2024, 1, 3, 19, 0, 0),
            'calendar_id': self.calendar_1.id,
        })
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'time_type': 'leave',
            'requires_allocation': False,
        })
        self.employee_emp.resource_calendar_id = self.calendar_1.id

        leave = self.env['hr.leave'].create({
            'name': 'Test new leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': global_leave.date_from,
            'request_date_to': global_leave.date_to,
        })
        self.assertEqual(leave.number_of_days, 0, 'It is a global leave')

        leave = self.env['hr.leave'].new({
            'name': 'Test new leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': global_leave.date_from,
            'request_date_to': global_leave.date_to,
        })
        self.assertEqual(leave.number_of_days, 0, 'It is a global leave')

        leave = self.env['hr.leave'].new({
            'name': 'Test new leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': global_leave.date_from - timedelta(days=1),
            'request_date_to': global_leave.date_to + timedelta(days=1),
        })
        self.assertEqual(leave.number_of_days, 2, 'There is a global leave')

    @freeze_time('2024-12-01')
    def test_global_leave_keeps_employee_resource_leave(self):
        """
            When a global leave is created, and it happens during a leave period of an employee,
            if the employee's leave is not fully covered by the global leave, the employee's leave
            should still have resource leaves linked to it.
        """
        employee = self.employee_emp
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'request_unit': 'hour',
            'leave_validation_type': 'both',
        })
        self.env['hr.leave.allocation'].create({
            'name': '20 days allocation',
            'holiday_status_id': leave_type.id,
            'number_of_days': 20,
            'employee_id': employee.id,
            'state': 'confirm',
            'date_from': date(2024, 12, 1),
            'date_to': date(2024, 12, 30),
        }).action_approve()

        partially_covered_leave = self.env['hr.leave'].create({
            'name': 'Holiday 1 week',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': datetime(2024, 12, 3, 7, 0),
            'request_date_to': datetime(2024, 12, 5, 18, 0),
        })
        partially_covered_leave.action_approve()

        global_leave = self.env['resource.calendar.leaves'].with_user(self.env.user).create({
            'name': 'Public holiday',
            'date_from': "2024-12-04 06:00:00",
            'date_to': "2024-12-04 23:00:00",
            'calendar_id': self.calendar_1.id,
        })

        # retrieve resource leaves linked to the employee's leave
        resource_leaves = self.env['resource.calendar.leaves'].search([
            ('holiday_id', '=', partially_covered_leave.id)
        ])
        self.assertTrue(resource_leaves, 'Resource leaves linked to the employee leave should exist.')

    @freeze_time('2025-05-11')
    def test_employee_leave_with_global_leave(self):
        """
            When an employee's leave is created, if there are any public holidays within the leave period,
            the number of leave days is reduced accordingly.
            eg,.
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            | Leave Requested  |  Leave State  | Public Holiday days  |  # days leave remains |
            |---------------------------------------------------------------------------------|
            |       5 Days     |    confirm    |        1 Days        |         4 Days        |
            |---------------------------------------------------------------------------------|
            |       4 Days     |   validate1   |        1 Days        |         3 Days        |
            |---------------------------------------------------------------------------------|
            |       3 Days     |    validate   |        1 Days        |         2 Days        |
            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        """
        user_david = mail_new_test_user(self.env, login='david', groups='base.group_user')
        user_timeoff_officer_david = mail_new_test_user(self.env, login='timeoff_officer', groups='base.group_user')

        employee_david = self.env['hr.employee'].create({
            'name': 'David Employee',
            'user_id': user_david.id,
            'leave_manager_id': user_timeoff_officer_david.id,
            'parent_id': self.employee_hruser.id,
            'department_id': self.rd_dept.id,
            'resource_calendar_id': self.calendar_1.id,
        })
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Sick Time Off',
            'time_type': 'leave',
            'requires_allocation': False,
            'leave_validation_type': 'both',
        })

        employee_leave = self.env['hr.leave'].create({
            'name': 'Holiday 5 days',
            'employee_id': employee_david.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': datetime(2025, 5, 12),
            'request_date_to': datetime(2025, 5, 16),
        })

        self.env['resource.calendar.leaves'].with_user(self.user_hrmanager).create({
            'name': 'Public holiday day 1',
            'date_from': datetime(2025, 5, 13),
            'date_to': datetime(2025, 5, 13, 23, 59),
            'calendar_id': employee_david.resource_calendar_id.id,
        })

        self.assertEqual(employee_leave.number_of_days, 4, 'Leave duration should be reduced because of public holiday day 1')

        employee_leave.with_user(user_timeoff_officer_david).action_approve()
        self.env['resource.calendar.leaves'].with_user(self.user_hrmanager).create({
            'name': 'Public holiday day 2',
            'date_from': datetime(2025, 5, 14),
            'date_to': datetime(2025, 5, 14, 23, 59),
            'calendar_id': employee_david.resource_calendar_id.id,
        })
        self.assertEqual(employee_leave.number_of_days, 3, 'Leave duration should be reduced because of public holiday day 2')

        employee_leave.with_user(self.user_hruser).action_approve()
        self.env['resource.calendar.leaves'].with_user(self.user_hrmanager).create({
            'name': 'Public holiday day 3',
            'date_from': datetime(2025, 5, 15),
            'date_to': datetime(2025, 5, 15, 23, 59),
            'calendar_id': employee_david.resource_calendar_id.id,
        })
        self.assertEqual(employee_leave.number_of_days, 2, 'Leave duration should be reduced because of public holiday day 3')
