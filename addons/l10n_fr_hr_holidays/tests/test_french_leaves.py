# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from datetime import date
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', 'post_install', '-at_install', 'french_leaves')
class TestFrenchLeaves(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        country_fr = cls.env.ref('base.fr')
        cls.company = cls.env['res.company'].create({
            'name': 'French Company',
            'country_id': country_fr.id,
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Louis',
            'sex': 'male',
            'birthday': '1973-03-29',
            'country_id': country_fr.id,
            'company_id': cls.company.id,
        })

        cls.time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Time Off',
            'requires_allocation': False,
            'request_unit': 'half_day',
        })
        cls.company.write({
            'l10n_fr_reference_leave_type': cls.time_off_type.id,
        })

        cls.base_calendar = cls.env['resource.calendar'].create({
            'name': 'default calendar',
        })

    def test_no_differences(self):
        # Base case that should not have a different behaviour
        self.company.resource_calendar_id = self.base_calendar
        self.employee.resource_calendar_id = self.base_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2021-09-06',
            'request_date_to': '2021-09-10',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_end_of_week(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
            ],
        })
        self.company.resource_calendar_id = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2021-09-06',
            'request_date_to': '2021-09-08',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_start_of_week(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
            ],
        })
        self.company.resource_calendar_id = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2021-09-08',
            'request_date_to': '2021-09-10',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_last_day_half(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
            ],
        })
        self.company.resource_calendar_id = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2021-09-10',
            'request_date_to': '2021-09-10',
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
        })
        # Since the employee works on the afternoon, the date_to is not post-poned
        self.assertEqual(leave.number_of_days, 0.5, 'The number of days should be equal to 0.5.')
        leave.request_date_from_period = 'pm'
        leave.request_date_to_period = 'pm'
        # This however should push the date_to
        self.assertEqual(leave.number_of_days, 2.5, 'The number of days should be equal to 2.5.')

    def test_calendar_with_holes(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
            ],
        })
        self.company.resource_calendar_id = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2021-09-06',
            'request_date_to': '2021-09-10',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_calendar_end_week_hole(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 17, 'break_hours': 1}),
            ],
        })
        self.company.resource_calendar_id = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2021-09-06',
            'request_date_to': '2021-09-08',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_leave_type_half_day_different_working_hours(self):
        """
        Test Case:
        ==========
        - Employee works from 8 to 12 and 14 to 17 Monday to Wednesday -> 7h/d
        - Company works from 9 to 12 and 13 to 18 Monday to Friday -> 8h/d
        - Employee requests 1 day off on Monday -> duration should be 1.0
        - Employee requests 0.5 day off on Monday morning or afternoon -> duration should be 0.5
        """
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 17, 'break_hours': 2}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 17, 'break_hours': 2}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 17, 'break_hours': 2}),
            ],
        })

        company_calendar = self.env['resource.calendar'].create({
            'name': 'Company Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 9, 'hour_to': 18, 'break_hours': 1}),
                (0, 0, {'dayofweek': '1', 'hour_from': 9, 'hour_to': 18, 'break_hours': 1}),
                (0, 0, {'dayofweek': '2', 'hour_from': 9, 'hour_to': 18, 'break_hours': 1}),
                (0, 0, {'dayofweek': '3', 'hour_from': 9, 'hour_to': 18, 'break_hours': 1}),
                (0, 0, {'dayofweek': '4', 'hour_from': 9, 'hour_to': 18, 'break_hours': 1}),
            ],
        })

        self.company.resource_calendar_id = company_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2024-07-29',
            'request_date_to': '2024-07-29',
            'request_date_from_period': 'am',
            'request_date_to_period': 'am',
        })
        self.assertEqual(leave.number_of_days, 0.5, 'The duration should be 0.5 day.')
        self.assertEqual(leave.date_from.date(), date(2024, 7, 29))
        self.assertEqual(leave.date_to.date(), date(2024, 7, 29))
        self.assertNotEqual(leave.number_of_hours, 8.0, 'Company and employee hours per day should not match in this case')

        leave.request_date_to_period = 'pm'
        leave.request_date_from_period = 'pm'
        self.assertEqual(leave.number_of_days, 0.5, 'The duration should be 0.5 day.')
        self.assertEqual(leave.date_from.date(), date(2024, 7, 29))
        self.assertEqual(leave.date_to.date(), date(2024, 7, 29))
        self.assertNotEqual(leave.number_of_hours, 8.0, 'Company and employee hours per day should not match in this case')

        self.time_off_type.request_unit = "day"
        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2024-07-22',
            'request_date_to': '2024-07-22',
        })
        self.assertEqual(leave.number_of_days, 1, 'The duration should be 1 day.')
        self.assertNotEqual(leave.number_of_hours, 8.0, 'Company and employee hours per day should not match in this case')
