# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.tests.common import users, warmup, tagged


@tagged('payslip_perf')
class TestPayrollPerformance(TestPayslipBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.jack = cls.env['hr.employee'].create({'name': 'Jack'})
        cls.employees = cls.richard_emp | cls.jack

        cls.env['hr.contract'].create([{
            'date_start': date(2018, 1, 1),
            'date_end': date(2018, 2, 1),
            'name': 'Contract for %s' % employee.name,
            'wage': 5000.0,
            'state': 'open',
            'employee_id': employee.id,
            'structure_type_id': cls.structure_type.id,
            'date_generated_from': datetime(2018, 1, 1, 0, 0),
            'date_generated_to': datetime(2018, 1, 1, 0, 0),
        } for employee in cls.employees])

    def reset_work_entries(self):
        self.employees.contract_id.write({
            'date_generated_from': datetime(2018, 1, 1, 0, 0),
            'date_generated_to': datetime(2018, 1, 1, 0, 0),
        })

    @users('__system__', 'admin')
    @warmup
    def test_performance_work_entry_generation(self):
        """ Work entry generation """
        with self.assertQueryCount(__system__=18, admin=20):
            self.employees.generate_work_entries(date(2018, 1, 1), date(2018, 1, 2))
        self.reset_work_entries()

    @users('__system__', 'admin')
    @warmup
    def test_performance_work_entry_unlink(self):
        """ Work entry unlink """
        work_entry = self.create_work_entry(datetime(2018, 1, 1, 7, 0), datetime(2018, 1, 1, 12, 0))
        self.create_work_entry(datetime(2018, 1, 1, 11, 0), datetime(2018, 1, 1, 17, 0))

        with self.assertQueryCount(__system__=14, admin=15):
            work_entry.unlink()

    @users('__system__', 'admin')
    @warmup
    def test_performance_work_entry_write_date(self):
        work_entry = self.create_work_entry(datetime(2018, 1, 1, 3, 0), datetime(2018, 1, 1, 4, 0))
        self.create_work_entry(datetime(2018, 1, 1, 11, 0), datetime(2018, 1, 1, 17, 0))

        with self.assertQueryCount(__system__=7, admin=8):
            work_entry.write({'date_stop': datetime(2018, 1, 1, 13, 0)})

    @users('__system__', 'admin')
    @warmup
    def test_performance_work_entry_write_date_batch(self):
        work_entry_1 = self.create_work_entry(datetime(2018, 1, 1, 3, 0), datetime(2018, 1, 1, 4, 0))
        work_entry_2 = self.create_work_entry(datetime(2018, 1, 1, 7, 0), datetime(2018, 1, 1, 11, 0))
        self.create_work_entry(datetime(2018, 1, 1, 11, 0), datetime(2018, 1, 1, 17, 0))

        with self.assertQueryCount(__system__=8, admin=9):
            (work_entry_1 | work_entry_2).write({'date_stop': datetime(2018, 1, 1, 13, 0)})

    @users('__system__', 'admin')
    @warmup
    def test_rule_parameter_cache(self):
        parameter = self.env['hr.rule.parameter'].create({
            'name': 'Test parameter',
            'code': 'test_parameter_cache',
        })
        self.env['hr.rule.parameter.value'].create({
            'rule_parameter_id': parameter.id,
            'date_from': date(2015, 10, 10),
            'parameter_value': 3
        })
        with self.assertQueryCount(__system__=0, admin=0):  # already cached from warmup
            self.env['hr.rule.parameter']._get_parameter_from_code('test_parameter_cache')
        parameter.unlink()
