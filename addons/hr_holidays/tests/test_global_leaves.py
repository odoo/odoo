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
            'date_from': "2022-03-07 00:00:00",
            'date_to': "2022-03-07 23:59:59",
        })

        cls.calendar_leave = cls.env['resource.calendar.leaves'].create({
            'name': 'Global Leave',
            'date_from': "2022-03-08 00:00:00",
            'date_to': "2022-03-08 23:59:59",
            'calendar_id': cls.calendar_1.id,
        })

    def test_leave_on_global_leave(self):
        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Leave',
                'date_from': "2022-03-07 00:00:00",
                'date_to': "2022-03-07 23:59:59",
                'calendar_id': self.calendar_1.id,
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Leave',
                'date_from': "2022-03-07 00:00:00",
                'date_to': "2022-03-07 23:59:59",
            })

    def test_leave_on_calendar_leave(self):
        self.env['resource.calendar.leaves'].create({
                'name': 'Correct Leave',
                'date_from': "2022-03-08 00:00:00",
                'date_to': "2022-03-08 23:59:59",
                'calendar_id': self.calendar_2.id,
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Leave',
                'date_from': "2022-03-08 00:00:00",
                'date_to': "2022-03-08 23:59:59",
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'Wrong Leave',
                'date_from': "2022-03-08 00:00:00",
                'date_to': "2022-03-08 23:59:59",
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
            'tz': 'Asia/Calcutta', # UTC +05:30
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
        # 8:00:00 for Asia/Calcutta (UTC +05:30) --> 2:30:00 in UTC
        self.assertEqual(global_leave.date_from, datetime(2023, 5, 15, 2, 30))
        self.assertEqual(global_leave.date_to, datetime(2023, 5, 15, 11, 30))
        # Note:
        # The user in Europe/Brussels timezone see 4:30 and not 2:30 because he is in UTC +02:00.
        # The user in Asia/Calcutta timezone (determined via the browser) see 8:00 because he is in UTC +05:30

    def test_global_leave_multi_companies(self):
        other_company = self.env['res.company'].create({'name': 'Other company'})
        calendar_other_company = self.env['resource.calendar'].create({
            'name': 'Classic 40h/week Other company',
            'tz': 'UTC',
            'company_id': other_company.id,
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
        other_company.resource_calendar_id = calendar_other_company
        self.env['resource.calendar.leaves'].with_company(other_company).create({
            'name': 'Global Leave Other company',
            'date_from': "2022-03-15 00:00:00",
            'date_to': "2022-03-15 23:59:59",
        })
        list_days = self.employee_emp.with_context(allowed_company_ids=[self.env.company.id, other_company.id], company_id=self.env.company.id)._get_unusual_days(date(2022, 3, 1), date(2022, 3, 30))
        self.assertTrue(list_days['2022-03-07']) #global leave from Yourcompany
        self.assertFalse(list_days['2022-03-15']) #global leave from Other company

        holidays = self.employee_emp.with_context(allowed_company_ids=[self.env.company.id, other_company.id], company_id=self.env.company.id)._get_public_holidays(date(2022, 3, 1), date(2022, 3, 30))
        self.assertEqual(len(holidays), 1)
        self.assertEqual(holidays.name, 'Global Leave')

        list_days = self.env['hr.employee'].with_context(allowed_company_ids=[self.env.company.id, other_company.id]).with_company(other_company)._get_unusual_days(date(2022, 3, 1), date(2022, 3, 30))
        self.assertFalse(list_days['2022-03-07']) #global leave from Yourcompany
        self.assertTrue(list_days['2022-03-15']) #global leave from Other company

        holidays = self.env['hr.employee'].with_context(allowed_company_ids=[self.env.company.id, other_company.id]).with_company(other_company)._get_public_holidays(date(2022, 3, 1), date(2022, 3, 30))
        self.assertEqual(len(holidays), 1)
        self.assertEqual(holidays.name, 'Global Leave Other company')
