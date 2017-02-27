# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Date
from odoo.tests.common import TransactionCase


class TestPayslipBase(TransactionCase):

    def setUp(self):
        super(TestPayslipBase, self).setUp()

        # Some salary rules references
        self.hra_rule_id = self.ref('hr_payroll.hr_salary_rule_houserentallowance1')
        self.conv_rule_id = self.ref('hr_payroll.hr_salary_rule_convanceallowance1')
        self.prof_tax_rule_id = self.ref('hr_payroll.hr_salary_rule_professionaltax1')
        self.pf_rule_id = self.ref('hr_payroll.hr_salary_rule_providentfund1')
        self.mv_rule_id = self.ref('hr_payroll.hr_salary_rule_meal_voucher')
        self.comm_rule_id = self.ref('hr_payroll.hr_salary_rule_sales_commission')

        # I create a new employee "Richard"
        self.richard_emp = self.env['hr.employee'].create({
            'name': 'Richard',
            'gender': 'male',
            'birthday': '1984-05-01',
            'country_id': self.ref('base.be'),
            'department_id': self.ref('hr.dep_rd')
        })

        # I create a salary structure for "Software Developer"
        self.developer_pay_structure = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'code': 'SD',
            'company_id': self.ref('base.main_company'),
            'rule_ids': [(4, [self.hra_rule_id, self.conv_rule_id, self.prof_tax_rule_id, self.pf_rule_id, self.mv_rule_id, self.comm_rule_id])]
        })

        # I create a contract for "Richard"
        self.env['hr.contract'].create({
            'date_end': Date.to_string((datetime.now() + timedelta(days=365))),
            'date_start': Date.today(),
            'name': 'Contract for Richard',
            'wage': 5000.0,
            'type_id': self.ref('hr_contract.hr_contract_type_emp'),
            'employee_id': self.richard_emp.id,
            'struct_id': self.developer_pay_structure.id,
            'working_hours': self.ref('resource.resource_calendar_std')
        })
