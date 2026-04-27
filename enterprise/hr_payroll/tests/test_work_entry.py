# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import pytz

from odoo.tests.common import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipBase


@tagged('work_entry')
class TestWorkEntry(TestPayslipBase):

    @classmethod
    def setUpClass(cls):
        super(TestWorkEntry, cls).setUpClass()
        cls.tz = pytz.timezone(cls.richard_emp.tz)
        cls.start = datetime(2015, 11, 1, 1, 0, 0)
        cls.end = datetime(2015, 11, 30, 23, 59, 59)
        cls.resource_calendar_id = cls.env['resource.calendar'].create({'name': 'Zboub'})
        contract = cls.env['hr.contract'].create({
            'date_start': cls.start.date() - relativedelta(days=5),
            'name': 'dodo',
            'resource_calendar_id': cls.resource_calendar_id.id,
            'wage': 1000,
            'employee_id': cls.richard_emp.id,
            'structure_type_id': cls.structure_type.id,
            'state': 'open',
            'date_generated_from': cls.end.date() + relativedelta(days=5),
        })
        cls.richard_emp.resource_calendar_id = cls.resource_calendar_id
        cls.richard_emp.contract_id = contract

    def test_time_normal_work_entry(self):
        # Normal attendances (global to all employees)
        work_entries = self.richard_emp.contract_id.generate_work_entries(self.start.date(), self.end.date())
        work_entries.action_validate()
        hours = self.richard_emp.contract_id.get_work_hours(self.start.date(), self.end.date())
        sum_hours = sum(v for k, v in hours.items() if k in self.env.ref('hr_work_entry.work_entry_type_attendance').ids)

        self.assertEqual(sum_hours, 168.0)

    def test_time_extra_work_entry(self):
        start = datetime(2015, 11, 1, 10, 0, 0)
        end = datetime(2015, 11, 1, 17, 0, 0)
        work_entry = self.env['hr.work.entry'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'contract_id': self.richard_emp.contract_id.id,
            'work_entry_type_id': self.work_entry_type.id,
            'date_start': start,
            'date_stop': end,
        })
        work_entry.action_validate()

        work_entries = self.richard_emp.contract_id.generate_work_entries(self.start.date(), self.end.date())
        work_entries.action_validate()
        hours = self.richard_emp.contract_id.get_work_hours(self.start.date(), self.end.date())
        sum_hours = sum(v for k, v in hours.items() if k in self.work_entry_type.ids)

        self.assertEqual(sum_hours, 7.0)

    def test_edge_timezone_work_entry(self):
        hk_resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'HK Calendar',
            'tz': 'Asia/Hong_Kong',
            'hours_per_day': 8,
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 7, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 7, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 7, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 7, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 7, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
            ]
        })
        hk_employee = self.env['hr.employee'].create({
            'name': 'HK Employee',
            'resource_calendar_id': hk_resource_calendar_id.id,
        })
        self.env.company.resource_calendar_id = hk_resource_calendar_id
        self.env['hr.contract'].create({
            'date_start': date(2023, 8, 1),
            'name': 'Test Contract',
            'resource_calendar_id': hk_resource_calendar_id.id,
            'wage': 1000,
            'employee_id': hk_employee.id,
            'state': 'open',
            'structure_type_id': self.structure_type.id,
        })
        work_entries = hk_employee.contract_id.generate_work_entries(date(2023, 8, 1), date(2023, 8, 31))
        work_entries.action_validate()
        hours = hk_employee.contract_id.get_work_hours(date(2023, 8, 1), date(2023, 8, 31))
        sum_hours = sum(v for k, v in hours.items() if k in self.env.ref('hr_work_entry.work_entry_type_attendance').ids)
        self.assertAlmostEqual(sum_hours, 184.0, places=2)
