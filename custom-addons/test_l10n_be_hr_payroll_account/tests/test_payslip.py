# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, time
from odoo.tests import common


class TestPayslipBase(common.TransactionCase):

    def setUp(self):
        super(TestPayslipBase, self).setUp()
        self.env.company.country_id = self.env.ref('base.be')
        self.employee = self.env['hr.employee'].create({
            'name': 'employee',
        })

    def check_payslip(self, name, payslip, values):
        for code, value in values.items():
            self.assertAlmostEqual(payslip.line_ids.filtered(lambda line: line.code == code).total, value)

    def create_contract(self, date_start, date_end=False, wage=2500):
        return self.env['hr.contract'].create({
            'name': 'Contract for %s' % self.employee.name,
            'wage': wage,
            'wage_on_signature': wage,
            'employee_id': self.employee.id,
            'state': 'open',
            'date_start': date_start,
            'date_end': date_end,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'internet': False,
            'mobile': False,
        })

    def create_payslip(self, contract, structure, date_start, date_end=False):
        return self.env['hr.payslip'].create({
            'name': '%s for %s' % (structure, self.employee),
            'employee_id': self.employee.id,
            'date_from': date_start,
            'date_to': date_end,
            'struct_id': structure.id,
            'contract_id': contract.id,
        })
