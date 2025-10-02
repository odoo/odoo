# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from datetime import date
from odoo.tests.common import TransactionCase, tagged

from zoneinfo import ZoneInfo
from datetime import datetime, timezone

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
            'unit_of_measure': 'day',
        })
        cls.company.write({
            'l10n_fr_reference_leave_type': cls.time_off_type.id,
        })

        cls.base_calendar = cls.env['resource.calendar'].create({
            'attendance_ids': [
                (0, 0,
                    {
                        'dayofweek': weekday,
                        'hour_from': hour,
                        'hour_to': hour + 4,
                    })
                for weekday in ['0', '1', '2', '3', '4']
                for hour in [8, 13]
            ],
            'name': 'Standard 40h/week',
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
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
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
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 17}),
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
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 17}),
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
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 17}),
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
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
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
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 14, 'hour_to': 17}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '1', 'hour_from': 14, 'hour_to': 17}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 14, 'hour_to': 17}),
            ],
        })

        company_calendar = self.env['resource.calendar'].create({
            'name': 'Company Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 9, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 18}),
                (0, 0, {'dayofweek': '1', 'hour_from': 9, 'hour_to': 12}),
                (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 18}),
                (0, 0, {'dayofweek': '2', 'hour_from': 9, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 18}),
                (0, 0, {'dayofweek': '3', 'hour_from': 9, 'hour_to': 12}),
                (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 18}),
                (0, 0, {'dayofweek': '4', 'hour_from': 9, 'hour_to': 12}),
                (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 18}),
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
        self.time_off_type.unit_of_measure = "day"
        leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2024-07-22',
            'request_date_to': '2024-07-22',
        })
        self.assertEqual(leave.number_of_days, 1, 'The duration should be 1 day.')
        self.assertNotEqual(leave.number_of_hours, 8.0, 'Company and employee hours per day should not match in this case')

    def test_leave_employee_different_schedule_from_company(self):
        self.company.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Company Calendar',
            'attendance_ids': [attendance for i in range(5) for attendance in [
                (0, 0, {'dayofweek': str(i), 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': str(i), 'hour_from': 13, 'hour_to': 17})]
            ]
        })
        self.employee.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [attendance for i in range(5) for attendance in [
                (0, 0, {'dayofweek': str(i), 'hour_from': 9, 'hour_to': 12}),
                (0, 0, {'dayofweek': str(i), 'hour_from': 13, 'hour_to': 17.50})]
            ]
        })

        leave_1 = self.env['hr.leave'].create({
            'name': 'Test leave',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2025-08-04',
            'request_date_to': '2025-08-04',
        })

        work_hours_data = leave_1.employee_id._list_work_time_per_day(
            leave_1.date_from,
            leave_1.date_to)

        self.assertEqual(work_hours_data[leave_1.employee_id.id][0][1], 7.50)

    def test_holiday_in_week(self):
        """
        Test Case:
        ==========
        - Employee works from Monday to Wednesday
        - Company works from Monday to Friday
        - Employee requests monday to wednesday off -> according to french law, he has to take all week (5 days)
        - In a given week thursday is a holiday -> in that week a whole week is 4 days -> 4 days off
        """
        employee_calendar = self.env['resource.calendar'].create({
            'name': 'Employee Calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 17}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
            ],
        })

        self.employee.resource_calendar_id = employee_calendar
        self.company.resource_calendar_id = self.base_calendar

        # Here we have to create a holiday with company, since the company is set based on the env
        # We also need to take into account that in the frontend this is a one day leave from
        # 00h00 to 23h59 , but in the server it is saved as utc, so we consider the current user tz
        # and subtract that from the holiday. With this, wherever you may be running the tests, the
        # result should be consistent
        tz = ZoneInfo(self.env.user.tz or 'UTC')
        self.env['resource.calendar.leaves'].with_company(self.company).create({
            'name': 'Public Holiday',
            'calendar_id': False,
            'date_from': datetime(2024, 12, 26, 0, 0, 0, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None),
            'date_to': datetime(2024, 12, 26, 23, 59, 59, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None),
            'resource_id': False,
        })

        leave = self.env['hr.leave'].create({
            'name': 'Test leave',
            'holiday_status_id': self.time_off_type.id,
            'employee_id': self.employee.id,
            'request_date_from': '2024-12-23',
            'request_date_to': '2024-12-25',
        })
        self.assertEqual(leave.number_of_days, 4.0, 'Public holidays for French part-time employees should be considered')
