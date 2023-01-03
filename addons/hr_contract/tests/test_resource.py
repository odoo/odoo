# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime
from pytz import utc, timezone

from odoo.addons.resource.models.resource import Intervals, sum_intervals
from odoo.fields import Date

from .common import TestContractCommon

class TestResource(TestContractCommon):

    @classmethod
    def setUpClass(cls):
        super(TestResource, cls).setUpClass()
        cls.calendar_richard = cls.env['resource.calendar'].create({'name': 'Calendar of Richard'})
        cls.employee.resource_calendar_id = cls.calendar_richard

        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': '35h calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
            ],
        })
        cls.calendar_35h._onchange_hours_per_day()  # update hours/day

        cls.contract_cdd = cls.env['hr.contract'].create({
            'date_start': Date.to_date('2021-09-01'),
            'date_end': Date.to_date('2021-10-31'),
            'name': 'First CDD Contract for Richard',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.0,
            'employee_id': cls.employee.id,
            'state': 'open',
        })
        cls.contract_cdi = cls.env['hr.contract'].create({
            'date_start': Date.to_date('2021-11-01'),
            'name': 'CDI Contract for Richard',
            'resource_calendar_id': cls.calendar_richard.id,
            'wage': 5000.0,
            'employee_id': cls.employee.id,
            'state': 'draft',
            'kanban_state': 'done',
        })

    def test_calendars_validity_within_period(self):
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
            new_contract = self.contract_cdd.copy()
            new_contract.employee_id = emp
            new_contract.state = 'open'
            new_contract = self.contract_cdi.copy()
            new_contract.employee_id = emp
            new_contract.state = 'draft'
            new_contract.kanban_state = 'done'

        start = utc.localize(datetime(2021, 9, 1, 0, 0, 0))
        end = utc.localize(datetime(2021, 11, 30, 23, 59, 59))
        with self.assertQueryCount(15):
            work_intervals, _ = (employees_test | self.employee).resource_id._get_valid_work_intervals(start, end)

        self.assertEqual(len(work_intervals), 51)

    def test_get_valid_work_intervals(self):
        start = timezone(self.employee.tz).localize(datetime(2021, 10, 24, 2, 0, 0))
        end = timezone(self.employee.tz).localize(datetime(2021, 11, 6, 23, 59, 59))
        work_intervals, _ = self.employee.resource_id._get_valid_work_intervals(start, end)
        sum_work_intervals = sum_intervals(work_intervals[self.employee.resource_id.id])
        self.assertEqual(75, sum_work_intervals, "Sum of the work intervals for the employee should be 35h+40h = 75h")
