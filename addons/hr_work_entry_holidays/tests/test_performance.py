# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase
from odoo.tests.common import users, warmup, tagged


@tagged('work_entry_holidays_perf')
class TestWorkEntryHolidaysPerformance(TestWorkEntryHolidaysBase):

    @classmethod
    def setUpClass(cls):
        super(TestWorkEntryHolidaysPerformance, cls).setUpClass()
        cls.jack = cls.env['hr.employee'].create({'name': 'Jack'})
        cls.employees = cls.richard_emp | cls.jack

        cls.env['hr.contract'].create([{
            'date_start': date(2018, 1, 1),
            'date_end': date(2018, 2, 1),
            'name': 'Contract for %s' % employee.name,
            'wage': 5000.0,
            'state': 'open',
            'employee_id': employee.id,
            'date_generated_from': datetime(2018, 1, 1, 0, 0),
            'date_generated_to': datetime(2018, 1, 1, 0, 0),
        } for employee in cls.employees])

    @users('__system__', 'admin')
    @warmup
    def test_performance_leave_validate(self):
        self.richard_emp.generate_work_entries(date(2018, 1, 1), date(2018, 1, 2))
        leave = self.create_leave(datetime(2018, 1, 1, 7, 0), datetime(2018, 1, 1, 18, 0))

        with self.assertQueryCount(__system__=101, admin=103):  # com 96/97
            leave.action_validate()
        leave.action_refuse()

    @users('__system__', 'admin')
    @warmup
    def test_performance_leave_write(self):
        leave = self.create_leave(datetime(2018, 1, 1, 7, 0), datetime(2018, 1, 1, 18, 0))

        with self.assertQueryCount(__system__=30, admin=38):
            leave.date_to = datetime(2018, 1, 1, 19, 0)
        leave.action_refuse()

    @users('__system__', 'admin')
    @warmup
    def test_performance_leave_create(self):
        with self.assertQueryCount(__system__=60, admin=60):
            leave = self.create_leave(datetime(2018, 1, 1, 7, 0), datetime(2018, 1, 1, 18, 0))
        leave.action_refuse()

    @users('__system__', 'admin')
    @warmup
    def test_performance_leave_confirm(self):
        leave = self.create_leave(datetime(2018, 1, 1, 7, 0), datetime(2018, 1, 1, 18, 0))
        leave.action_draft()
        with self.assertQueryCount(__system__=43, admin=42):
            leave.action_confirm()
        leave.state = 'refuse'


@tagged('work_entry_perf')
class TestWorkEntryHolidaysPerformancesBigData(TestWorkEntryHolidaysBase):

    @classmethod
    def setUpClass(cls):
        super(TestWorkEntryHolidaysPerformancesBigData, cls).setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'A company'})

        cls.paid_time_off = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'request_unit': 'day',
            'leave_validation_type': 'both',
            'company_id': cls.company.id,
            'requires_allocation': 'no',
        })

        cls.employees = cls.env['hr.employee'].create([{
            'name': 'Employee %s' % i,
            'company_id': cls.company.id
        } for i in range(100)])

        cls.contracts = cls.env['hr.contract'].create([{
            'date_start': date(2018, 1, 1),
            'date_end': False,
            'name': 'Contract for %s' % employee.name,
            'wage': 5000.0,
            'state': 'open',
            'employee_id': employee.id,
            'date_generated_from': datetime(2018, 1, 1, 0, 0),
            'date_generated_to': datetime(2018, 1, 1, 0, 0),
        } for employee in cls.employees])

        cls.leaves = cls.env['hr.leave'].create([{
            'name': 'Holiday - %s' % employee.name,
            'employee_id': employee.id,
            'holiday_status_id': cls.paid_time_off.id,
            'request_date_from': date(2020, 8, 3),
            'request_date_to': date(2020, 8, 7),
        } for employee in cls.employees])
        cls.leaves._compute_date_from_to()
        cls.leaves.action_approve()
        cls.leaves.action_validate()

    def test_work_entries_generation_perf(self):
        # Test Case 7: Try to generate work entries for
        # a hundred employees over a month
        with self.assertQueryCount(__system__=407, admin=2807):  # com: 402 / 2807
            work_entries = self.contracts.generate_work_entries(date(2020, 7, 1), date(2020, 8, 31))

        # Original work entries to generate when we don't adapt date_generated_from and
        # date_generated_to when they are equal for old contracts: 138300
        self.assertEqual(len(work_entries), 8800)
