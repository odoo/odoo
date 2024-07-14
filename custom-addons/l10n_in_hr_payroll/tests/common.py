# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPayrollCommon(TransactionCase):

    def setUp(self):
        super(TestPayrollCommon, self).setUp()

        self.Bank = self.env['res.partner.bank']
        self.Employee = self.env['hr.employee']
        self.PayslipRun = self.env['hr.payslip.run']
        self.PayslipEmployee = self.env['hr.payslip.employees']
        self.Advice = self.env['hr.payroll.advice']

        self.partner = self.env.ref('base.partner_admin')
        self.bank_1 = self.env.ref('base.res_bank_1')
        self.in_country = self.env.ref('base.in')
        self.rd_dept = self.env.ref('hr.dep_rd')
        self.employee_fp = self.env.ref('hr.employee_admin')
        self.employee_al = self.env.ref('hr.employee_al')

        # I create a new bank record
        self.res_bank = self.Bank.create({
            'acc_number': '3025632343043',
            'partner_id': self.partner.id,
            'acc_type': 'bank',
            'bank_id': self.bank_1.id
        })

        # I create a new employee “Rahul”
        self.rahul_emp = self.Employee.create({
            'name': 'Rahul',
            'country_id': self.in_country.id,
            'department_id': self.rd_dept.id,
            'bank_account_id': self.res_bank.id
        })
