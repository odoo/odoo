# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from pytz import utc, timezone

from odoo.tools.intervals import Intervals
from odoo.fields import Date
from odoo.tools.date_utils import sum_intervals

from .common import TestHrCommon


class TestResource(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super(TestResource, cls).setUpClass()
        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})
        cls.employee_niv = cls.env['hr.employee'].create({
            'name': 'Sharlene Rhodes',
            'departure_date': '2022-06-01',
            'resource_calendar_id': cls.calendar_40h.id,
        })
        cls.employee_niv_create_date = '2021-01-01 10:00:00'
        cls.env.cr.execute("UPDATE hr_employee SET create_date=%s WHERE id=%s",
                           (cls.employee_niv_create_date, cls.employee_niv.id))

        cls.calendar_richard = cls.env['resource.calendar'].create({'name': 'Calendar of Richard'})
        cls.employee.resource_calendar_id = cls.calendar_richard

        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': '35h calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
            ],
        })

        cls.contract_cdd = cls.employee.version_id
        cls.contract_cdd.write({
            'date_version': Date.to_date('2021-09-01'),
            'contract_date_start': Date.to_date('2021-09-01'),
            'contract_date_end': Date.to_date('2021-10-31'),
            'name': 'First CDD Contract for Richard',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.0,
            'employee_id': cls.employee.id,
        })
        cls.contract_cdi_values = {
            'date_version': Date.to_date('2021-11-01'),
            'contract_date_start': Date.to_date('2021-11-01'),
            'contract_date_end': False,
            'name': 'CDI Contract for Richard',
            'resource_calendar_id': cls.calendar_richard.id,
            'wage': 5000.0,
            'employee_id': cls.employee.id,
        }

    def test_calendars_validity_within_period_default(self):
        calendars = self.employee_niv.resource_id._get_calendars_validity_within_period(
            utc.localize(datetime(2021, 7, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 7, 30, 17, 0, 0)),
        )
        interval = Intervals([(
            utc.localize(datetime(2021, 7, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 7, 30, 17, 0, 0)),
            self.env['resource.calendar.attendance']
        )])

        self.assertEqual(1, len(calendars), "The dict returned by calendars validity should only have 1 entry")
        self.assertEqual(1, len(calendars[self.employee_niv.resource_id.id]), "Niv should only have one calendar")
        niv_entry = calendars[self.employee_niv.resource_id.id]
        niv_calendar = next(iter(niv_entry))
        self.assertEqual(niv_calendar, self.calendar_40h, "It should be Niv's Calendar")
        self.assertFalse(niv_entry[niv_calendar] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - niv_entry[niv_calendar], "Calendar validity should cover all interval")

    def test_calendars_validity_within_period_creation(self):
        calendars = self.employee_niv.resource_id._get_calendars_validity_within_period(
            utc.localize(datetime(2020, 12, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 1, 31, 17, 0, 0)),
        )
        interval = Intervals([(
            utc.localize(datetime(2020, 12, 1, 8, 0, 0)),
            utc.localize(datetime(2021, 1, 31, 17, 0, 0)),
            self.env['resource.calendar.attendance']
        )])
        niv_entry = calendars[self.employee_niv.resource_id.id]
        self.assertFalse(niv_entry[self.calendar_40h] - interval, "Interval should cover all calendar's validity")
        self.assertFalse(interval - niv_entry[self.calendar_40h], "Calendar validity should cover all interval")

    def test_availability_hr_infos_resource(self):
        """ Ensure that all the hr infos needed to display the avatar popover card
            are available on the model resource.resource, even if the employee is archived
        """
        user = self.env['res.users'].create([{
            'name': 'Test user',
            'login': 'test',
            'email': 'test@odoo.perso',
            'phone': '+32488990011',
        }])
        department = self.env['hr.department'].create([{
            'name': 'QA',
        }])
        resource = self.env['resource.resource'].create([{
            'name': 'Test resource',
            'user_id': user.id,
        }])
        employee = self.env['hr.employee'].create([{
            'name': 'Test employee',
            'active': False,
            'user_id': user.id,
            'job_title': 'Tester',
            'department_id': department.id,
            'work_email': 'test@odoo.pro',
            'work_phone': '+32800100100',
            'resource_id': resource.id,
        }])
        for field in 'email', 'phone', 'im_status':
            self.assertEqual(resource[field], user[field])
        for field in 'job_title', 'department_id', 'work_email', 'work_phone', 'show_hr_icon_display', 'hr_icon_display':
            self.assertEqual(resource[field], employee[field])

    def test_calendars_validity_within_period(self):
        self.employee.create_version(self.contract_cdi_values)
        tz = timezone(self.employee.tz)
        calendars = self.employee.resource_id._get_calendars_validity_within_period(
            tz.localize(datetime(2021, 10, 1, 0, 0, 0)),
            tz.localize(datetime(2021, 12, 1, 0, 0, 0)),
        )
        interval_35h = Intervals([(
            tz.localize(datetime(2021, 10, 1, 0, 0, 0)),
            tz.localize(datetime.combine(date(2021, 10, 31), datetime.max.time())),
            self.env['resource.calendar.attendance']
        )])
        interval_40h = Intervals([(
            tz.localize(datetime(2021, 11, 1, 0, 0, 0)),
            tz.localize(datetime(2021, 12, 1, 0, 0, 0)),
            self.env['resource.calendar.attendance']
        )])

        self.assertEqual(1, len(calendars), "The dict returned by calendars validity should only have 1 entry")
        self.assertEqual(2, len(calendars[self.employee.resource_id.id]), "Jean should only have one calendar")
        richard_entries = calendars[self.employee.resource_id.id]
        for calendar in richard_entries:
            self.assertTrue(calendar in (self.calendar_35h | self.calendar_richard), "Each calendar should be listed")
            if calendar == self.calendar_35h:
                self.assertFalse(richard_entries[calendar] - interval_35h, "Interval 35h should cover all calendar 35h validity")
                self.assertFalse(interval_35h - richard_entries[calendar], "Calendar 35h validity should cover all interval 35h")
            elif calendar == self.calendar_richard:
                self.assertFalse(richard_entries[calendar] - interval_40h, "Interval 40h should cover all calendar 40h validity")
                self.assertFalse(interval_40h - richard_entries[calendar], "Calendar 40h validity should cover all interval 40h")

    def test_queries(self):
        employees_test = self.env['hr.employee'].create([{
            'name': 'Employee ' + str(i),
        } for i in range(0, 50)])
        for emp in employees_test:
            self.contract_cdd.copy({'employee_id': emp.id})
            self.contract_cdi_values['employee_id'] = emp.id
            self.employee.create_version(self.contract_cdi_values)

        start = utc.localize(datetime(2021, 9, 1, 0, 0, 0))
        end = utc.localize(datetime(2021, 11, 30, 23, 59, 59))
        with self.assertQueryCount(165):
            work_intervals, _ = (employees_test | self.employee).resource_id._get_valid_work_intervals(start, end)

        self.assertEqual(len(work_intervals), 51)

    def test_get_valid_work_intervals(self):
        self.employee.create_version(self.contract_cdi_values)
        start = timezone(self.employee.tz).localize(datetime(2021, 10, 24, 2, 0, 0))
        end = timezone(self.employee.tz).localize(datetime(2021, 11, 6, 23, 59, 59))
        work_intervals, _ = self.employee.resource_id._get_valid_work_intervals(start, end)
        sum_work_intervals = sum_intervals(work_intervals[self.employee.resource_id.id])
        self.assertEqual(75, sum_work_intervals, "Sum of the work intervals for the employee should be 35h+40h = 75h")

    def test_multi_contract_attendance(self):
        """ Verify whether retrieving an employee's calendar attendances can
            handle multiple contracts with different calendars.
        """

        date_from = utc.localize(datetime(2021, 10, 1, 0, 0, 0))
        date_to = utc.localize(datetime(2021, 11, 30, 0, 0, 0))

        attendances = self.employee._get_calendar_attendances(date_from, date_to)
        self.assertEqual(21 * 7, attendances['hours'],
            "Attendances should only include running or finished contracts.")

        self.employee.create_version(self.contract_cdi_values)

        attendances = self.employee._get_calendar_attendances(date_from, date_to)
        self.assertEqual(21 * 7 + 21 * 8, attendances['hours'],
            "Attendances should add up multiple contracts with varying work weeks.")

    def test_alter_resource_calendar_of_resouce(self):
        self.assertEqual(self.employee.resource_calendar_id, self.employee.resource_id.calendar_id)
        self.assertEqual(self.employee.version_id.resource_calendar_id, self.employee.resource_id.calendar_id)
        self.employee.resource_id.write({'calendar_id': self.calendar_40h})
        self.assertEqual(self.employee.resource_calendar_id, self.employee.resource_id.calendar_id)
        self.assertEqual(self.employee.version_id.resource_calendar_id, self.employee.resource_id.calendar_id)
