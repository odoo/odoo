# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

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
        self.Company = self.env['res.company']
        self.partner = self.env.ref('base.partner_admin')
        self.bank_1 = self.env.ref('base.res_bank_1')
        self.in_country = self.env.ref('base.in')
        self.rd_dept = self.env.ref('hr.dep_rd')
        self.employee_fp = self.env.ref('hr.employee_admin')
        self.employee_al = self.env.ref('hr.employee_al')

        self.company_in = self.Company.create({
            'name': 'Company IN',
            'country_code': 'IN',
        })

        self.in_bank = self.env['res.bank'].create({
            'name': 'Bank IN',
            'bic': 'ABCD0123456'
        })

        # I create a new employee “Rahul”
        self.rahul_emp = self.Employee.create({
            'name': 'Rahul',
            'country_id': self.in_country.id,
            'department_id': self.rd_dept.id,
            'company_id': self.company_in.id
        })

        # I create a new employee “Rahul”
        self.jethalal_emp = self.Employee.create({
            'name': 'Jethalal',
            'country_id': self.in_country.id,
            'department_id': self.rd_dept.id,
            'company_id': self.company_in.id,
        })

        self.res_bank = self.Bank.create({
            'acc_number': '3025632343043',
            'partner_id': self.rahul_emp.work_contact_id.id,
            'acc_type': 'bank',
            'bank_id': self.in_bank.id,
            'allow_out_payment': True,
        })
        self.rahul_emp.bank_account_id = self.res_bank

        self.res_bank_1 = self.Bank.create({
            'acc_number': '3025632343044',
            'partner_id': self.jethalal_emp.work_contact_id.id,
            'acc_type': 'bank',
            'bank_id': self.in_bank.id,
            'allow_out_payment': True,
        })
        self.jethalal_emp.bank_account_id = self.res_bank_1

        self.contract_rahul = self.env['hr.contract'].create({
            'date_start': date(2023, 1, 1),
            'date_end':  date(2023, 1, 31),
            'name': 'Rahul Probation contract',
            'wage': 5000.0,
            'employee_id': self.rahul_emp.id,
            'state': 'open',
            'hr_responsible_id': self.employee_fp.id,
        })

        self.contract_jethalal = self.env['hr.contract'].create({
            'date_start': date(2023, 1, 1),
            'date_end':  date(2023, 1, 31),
            'name': 'Jethalal Probation contract',
            'wage': 5000.0,
            'employee_id': self.jethalal_emp.id,
            'state': 'open',
            'hr_responsible_id': self.employee_fp.id,
        })
