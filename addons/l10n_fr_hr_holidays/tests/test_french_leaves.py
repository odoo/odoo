# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged

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
            'gender': 'other',
            'birthday': '1973-03-29',
            'country_id': country_fr.id,
            'company_id': cls.company.id,
        })

        cls.time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Time Off',
            'requires_allocation': 'no',
        })

        cls.base_calendar = cls.env['resource.calendar'].create({
            'name': 'default calendar',
        })

    def test_no_differences(self):
        # Base case that should not have a different behaviour
        self.company.time_off_reference_calendar = self.base_calendar
        self.employee.resource_calendar_id = self.base_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-06',
            'date_to': '2021-09-10 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_end_of_week(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.company.time_off_reference_calendar = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-06',
            'date_to': '2021-09-08 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_start_of_week(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.company.time_off_reference_calendar = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-08',
            'date_to': '2021-09-10 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_last_day_half(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.company.time_off_reference_calendar = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-10',
            'date_to': '2021-09-10 12:00:00',
            'request_date_from': '2021-09-10',
            'request_date_to': '2021-09-10 12:00:00',
            'request_unit_half': True,
            'request_date_from_period': 'am',
        })
        # Since the employee works on the afternoon, the date_to (l10n_fr_date_to) is not post-poned
        self.assertEqual(leave.number_of_days, 0.5, 'The number of days should be equal to 0.5.')
        leave.request_date_from_period = 'pm'
        # This however should push the date_to (l10n_fr_date_to)
        self.assertEqual(leave.number_of_days, 2.5, 'The number of days should be equal to 2.5.')


    def test_calendar_with_holes(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.company.time_off_reference_calendar = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-06',
            'date_to': '2021-09-10 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_calendar_end_week_hole(self):
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.company.time_off_reference_calendar = self.base_calendar
        self.employee.resource_calendar_id = employee_calendar

        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-06',
            'date_to': '2021-09-08 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')

    def test_2_weeks_calendar(self):
        company_calendar = self.env['resource.calendar'].create({
            'name': 'Company Calendar',
            'two_weeks_calendar': True,
            'attendance_ids': [
                (0, 0, {'week_type': '0', 'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'week_type': '0', 'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'week_type': '0', 'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'week_type': '0', 'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'week_type': '0', 'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'week_type': '0', 'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'week_type': '0', 'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'week_type': '0', 'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'week_type': '0', 'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'week_type': '0', 'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),

                (0, 0, {'week_type': '1', 'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'week_type': '1', 'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'week_type': '1', 'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'week_type': '1', 'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'week_type': '1', 'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'week_type': '1', 'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })
        self.company.time_off_reference_calendar = company_calendar
        self.employee.resource_calendar_id = employee_calendar

        # Week type 0
        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-06',
            'date_to': '2021-09-08 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 5, 'The number of days should be equal to 5.')
        leave.unlink()

        # Week type 1
        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-13',
            'date_to': '2021-09-15 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 3, 'The number of days should be equal to 3.')
        leave.unlink()

        # Both ending with week type 1
        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-06',
            'date_to': '2021-09-15 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 8, 'The number of days should be equal to 3.')
        leave.unlink()

        # Both ending with week type 0
        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'date_from': '2021-09-13',
            'date_to': '2021-09-22 23:59:59',
        })
        self.assertEqual(leave.number_of_days, 8, 'The number of days should be equal to 3.')
        leave.unlink()
