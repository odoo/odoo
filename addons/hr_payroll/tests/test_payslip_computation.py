# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import pytz
from dateutil.relativedelta import relativedelta
from odoo import exceptions
from odoo.tests.common import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipBase


class TestPayslipComputation(TestPayslipBase):

    def setUp(self):
        super(TestPayslipComputation, self).setUp()

        self.richard_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
            # wage: 5000, average/day (over 3months/13weeks): 230.77
            'contract_id': self.env['hr.contract'].search([('employee_id', '=', self.richard_emp.id)]).id,
        })

        # paid
        self.worked_day_line_work = self.env['hr.payslip.worked_days'].create({
            'name': "Work hard",
            'benefit_type_id': self.benefit_type.id,
            'number_of_days': 5,
            'number_of_hours': 40,
            'payslip_id': self.richard_payslip.id,
        })

        # paid
        self.worked_day_line_paid_leave = self.env['hr.payslip.worked_days'].create({
            'name': "Chill hard and earn money :D",
            'benefit_type_id': self.benefit_type_leave.id,
            'number_of_days': 3,
            'number_of_hours': 24,
            'payslip_id': self.richard_payslip.id,
        })

        # unpaid
        self.worked_day_line_unpaid = self.env['hr.payslip.worked_days'].create({
            'name': "Chill hard but unpaid :/",
            'benefit_type_id': self.benefit_type_unpaid.id,
            'number_of_days': 2,
            'number_of_hours': 16,
            'payslip_id': self.richard_payslip.id,
        })

    def test_compute_deduction(self):
        # 2 unpaid days
        self.assertAlmostEqual(self.richard_payslip.unpaid_amount, 461.54)

    def test_lines_amount(self):
        # 8 paid days in total => paid amount: 5000 * 8/10
        self.richard_payslip._compute_worked_days_lines_amount()
        self.assertEqual(self.worked_day_line_work.amount, 2836.54)  # 5/8 paid days
        self.assertEqual(self.worked_day_line_paid_leave.amount, 1701.92)  # 3/8 paid days
        self.assertEqual(self.worked_day_line_unpaid.amount, 0.0)

    def test_total(self):
        self.richard_payslip._compute_worked_days_lines_amount()
        self.assertEqual(sum(self.richard_payslip.worked_days_line_ids.mapped('amount')) + self.richard_payslip.unpaid_amount, 5000)
