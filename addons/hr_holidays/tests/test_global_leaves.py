# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
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
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
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
            'name': 'Global Leave',
            'date_from': date(2022, 3, 7),
            'date_to': date(2022, 3, 7),
        })

        cls.calendar_leave = cls.env['resource.calendar.leaves'].create({
            'name': 'Global Leave',
            'date_from': date(2022, 3, 8),
            'date_to': date(2022, 3, 8),
            'calendar_id': cls.calendar_1.id,
        })

    def test_leave_on_global_leave(self):
        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Leave',
                'date_from': date(2022, 3, 7),
                'date_to': date(2022, 3, 7),
                'calendar_id': self.calendar_1.id,
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Leave',
                'date_from': date(2022, 3, 7),
                'date_to': date(2022, 3, 7),
            })

    def test_leave_on_deleted_global_leave(self):
        public_leave = self.env['resource.calendar.leaves'].create({
            'name': 'Public Time Off',
            'date_from': datetime(2024, 2, 20, 0, 0),
            'date_to': datetime(2024, 2, 22, 23, 59),
            'company_id': self.employee_emp.company_id.id,
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'no',
            'leave_validation_type': 'both',
            'responsible_id': self.user_hrmanager_id,
        })
        self.env['hr.leave.allocation'].create({
            'employee_id': self.employee_emp_id,
            'name': '2 days allocation',
            'holiday_status_id': leave_type.id,
            'number_of_days': 2,
            'state': 'confirm',
            'date_from': date(2024, 2, 1),
            'date_to': date(2024, 2, 29),
        })
        covered_leave_1 = self.env['hr.leave'].create({
            'name': 'Covered Leave',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': leave_type.id,
            'date_from': datetime(2024, 2, 19, 7, 0),
            'date_to': datetime(2024, 2, 20, 18, 0),
        })
        self.assertEqual(covered_leave_1.number_of_days, 1, 'The leave should have a duration of 1 day.')
        covered_leave_2 = self.env['hr.leave'].create({
            'name': 'Covered Leave',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': leave_type.id,
            'date_from': datetime(2024, 2, 21, 7, 0),
            'date_to': datetime(2024, 2, 21, 18, 0),
        })
        self.assertEqual(covered_leave_2.number_of_days, 0, 'The leave should have a duration of 0 days.')
        covered_leave_3 = self.env['hr.leave'].create({
            'name': 'Covered Leave',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': leave_type.id,
            'date_from': datetime(2024, 2, 22, 7, 0),
            'date_to': datetime(2024, 2, 23, 18, 0),
        })
        self.assertEqual(covered_leave_3.number_of_days, 1, 'The leave should have a duration of 1 day.')

        public_leave.unlink()
        self.assertEqual(covered_leave_1.active, True, 'The partially covered leave should still be active.')
        self.assertEqual(covered_leave_1.number_of_days, 1, 'The leave should have a duration of 1 day.')
        self.assertEqual(covered_leave_2.active, False, 'The covered leave should be archived.')
        self.assertEqual(covered_leave_3.active, True, 'The partially covered leave should still be active.')
        self.assertEqual(covered_leave_3.number_of_days, 1, 'The leave should have a duration of 1 day.')

    def test_leave_on_calendar_leave(self):
        self.env['resource.calendar.leaves'].create({
                'name': 'Correct Leave',
                'date_from': date(2022, 3, 8),
                'date_to': date(2022, 3, 8),
                'calendar_id': self.calendar_2.id,
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Leave',
                'date_from': date(2022, 3, 8),
                'date_to': date(2022, 3, 8),
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Leave',
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

    @freeze_time('2024-12-01')
    def test_global_leave_keeps_employee_resource_leave(self):
        """
            When a global leave is created, and it happens during a leave period of an employee,
            if the employee's leave is not fully covered by the global leave, the employee's leave
            should still have resource leaves linked to it.
        """
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'no',
            'leave_validation_type': 'both',
            'responsible_id': self.user_hrmanager_id,
        })
        self.env['hr.leave.allocation'].create({
            'employee_id': self.employee_emp_id,
            'name': '5 days allocation',
            'holiday_status_id': leave_type.id,
            'number_of_days': 5,
            'state': 'confirm',
            'date_from': date(2024, 12, 1),
            'date_to': date(2024, 12, 30),
        })
        partially_covered_leave = self.env['hr.leave'].create({
            'name': 'Covered Leave',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': leave_type.id,
            'date_from': datetime(2024, 12, 3, 7, 0),
            'date_to': datetime(2024, 12, 5, 18, 0),
        })
        partially_covered_leave.action_validate()

        global_leave = self.env['resource.calendar.leaves'].with_user(self.env.user).create({
            'name': 'Public holiday',
            'date_from': "2024-12-4 06:00:00",
            'date_to': "2024-12-4 23:00:00",
            'calendar_id': self.calendar_1.id,
        })

        # retrieve resource leaves linked to the employee's leave
        resource_leaves = self.env['resource.calendar.leaves'].search([
            ('holiday_id', '=', partially_covered_leave.id)
        ])
        self.assertTrue(resource_leaves, 'Resource leaves linked to the employee leave should exist.')
