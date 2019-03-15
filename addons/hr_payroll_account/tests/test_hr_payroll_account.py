# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from datetime import datetime, timedelta
from dateutil import relativedelta

from odoo import fields, tools
from odoo.modules.module import get_module_resource
from odoo.tests import common


class TestHrPayrollAccount(common.TransactionCase):

    def _load(self, module, *args):
        tools.convert_file(
            self.cr, 'hr_payroll_account',
            get_module_resource(module, *args), {}, 'init', False, 'test', self.registry._assertion_report)

    def setUp(self):
        super(TestHrPayrollAccount, self).setUp()

        self._load('account', 'test', 'account_minimal_test.xml')

        self.res_partner_bank = self.env['res.partner.bank'].create({
            'acc_number': '001-9876543-21',
            'partner_id': self.ref('base.res_partner_12'),
            'acc_type': 'bank',
            'bank_id': self.ref('base.res_bank_1'),
        })

        self.hr_employee_john = self.env['hr.employee'].create({
            'address_home_id': self.ref('base.res_partner_address_2'),
            'address_id': self.ref('base.res_partner_address_27'),
            'birthday': '1984-05-01',
            'children': 0.0,
            'country_id': self.ref('base.in'),
            'department_id': self.ref('hr.dep_rd'),
            'gender': 'male',
            'marital': 'single',
            'name': 'John',
            'bank_account_id': self.res_partner_bank.bank_id.id,
        })

        # Create account journal.
        self.hr_contract_john = self.env['hr.contract'].create({
            'date_end': fields.Date.to_string(datetime.now() + timedelta(days=365)),
            'date_start': fields.Date.today(),
            'name': 'Contract for John',
            'wage': 5000.0,
            'employee_id': self.hr_employee_john.id,
            'structure_type_id': self.env.ref('hr_payroll.structure_type_employee').id,
            'journal_id': self.ref('hr_payroll_account.expenses_journal'),
        })

        self.hr_payslip = self.env['hr.payslip'].create({
            'employee_id': self.hr_employee_john.id,
            'journal_id': self.ref('hr_payroll_account.expenses_journal'),
            'name': 'Test Payslip',
        })

    def test_00_hr_payslip(self):
        """ checking the process of payslip. """

        self.hr_payslip.date_from = time.strftime('%Y-%m-01')
        self.hr_payslip.date_to = str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]
        self.hr_payslip.onchange_employee()
        self.hr_payslip._onchange_struct_id()

        # I assign the amount to Input data.
        payslip_input = self.env['hr.payslip.input'].search([('payslip_id', '=', self.hr_payslip.id)])
        payslip_input.write({'amount': 5.0})

        # I verify the payslip is in draft state.
        self.assertEqual(self.hr_payslip.state, 'draft', 'State not changed!')

        # I click on "Compute Sheet" button.
        context = {"lang": "en_US", "tz": False, "active_model": 'hr.payslip', "department_id": False, "section_id": False}
        self.hr_payslip.with_context(context).compute_sheet()

        # I want to check cancel button. So I first cancel the sheet then make it set to draft.
        self.hr_payslip.action_payslip_cancel()
        self.assertEqual(self.hr_payslip.state, 'cancel', "Payslip is rejected.")
        self.hr_payslip.action_payslip_draft()

        # Confirm Payslip
        self.hr_payslip.action_payslip_done()

        # I verify that the Accounting Entries are created.
        self.assertTrue(self.hr_payslip.move_id, 'Accounting Entries has not been created')

        # I verify that the payslip is in done state.
        self.assertEqual(self.hr_payslip.state, 'done', 'State not changed!')
