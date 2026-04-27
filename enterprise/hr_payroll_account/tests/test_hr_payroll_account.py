# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import odoo.tests

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, Command
from odoo.tests import Form
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


@odoo.tests.tagged('post_install', '-at_install')
class TestHrPayrollAccountCommon(TestPayslipContractBase):

    @classmethod
    def setUpClass(cls):
        super(TestHrPayrollAccountCommon, cls).setUpClass()

        cls.work_contact = cls.env['res.partner'].create({'name': 'A work contact'})
        cls.env['res.partner.bank'].create({
            'acc_number': 'IT22M8576110068R4A56E760901',
            'partner_id': cls.work_contact.id,
            'allow_out_payment': True,
        })

        cls.work_address = cls.env['res.partner'].create({'name': 'A work address'})

        partner_john = cls.env['res.partner'].create({
            'name': 'John',
            'is_company': True,
        })
        john_bank = cls.env['res.bank'].create({'name': 'ING'})
        partner_bank_john = cls.env['res.partner.bank'].create({
            'acc_number': 'IT22M8576110068R4A56E760901',
            'partner_id': partner_john.id,
            'bank_id': john_bank.id,
            'allow_out_payment': True,
        })

        cls.hr_employee_john = cls.env['hr.employee'].create({
            'work_contact_id': partner_john.id,
            'address_id': cls.work_address.id,
            'birthday': '1984-05-01',
            'children': 0.0,
            'country_id': cls.env.ref('base.in').id,
            'gender': 'male',
            'marital': 'single',
            'name': 'John',
            'bank_account_id': partner_bank_john.id,
        })

        salary_account = cls.env['account.account'].create({
            'name': "Salary Expense",
            'code': "030303",
            'account_type': "expense",
        })

        salaries_journal = cls.env['account.journal'].create({
            'name': 'Test Salaries',
            'type': 'general',
            'code': 'SLR-TEST',
            'default_account_id': salary_account.id,
        })

        cls.hr_employee_mark = cls.env['hr.employee'].create({
            'work_contact_id': cls.work_contact.id,
            'address_id': cls.work_address.id,
            'birthday': '1984-05-01',
            'children': 0.0,
            'country_id': cls.env.ref('base.in').id,
            'gender': 'male',
            'marital': 'single',
            'name': 'Mark',
        })

        cls.account_journal = cls.env['account.journal'].create({
            'name' : 'MISC',
            'code' : 'MSC',
            'type' : 'general',
        })

        cls.hr_structure_softwaredeveloper = cls.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'rule_ids': [
                (0, 0, {
                    'name': 'Basic Salary',
                    'amount_select': 'percentage',
                    'amount_percentage': 100,
                    'amount_percentage_base': 'contract.wage',
                    'code': 'BASIC',
                    'category_id': cls.env.ref('hr_payroll.BASIC').id,
                    'sequence': 1,
                }), (0, 0, {
                    'name': 'Provident Fund',
                    'amount_select': 'percentage',
                    'sequence': 120,
                    'amount_percentage': -12.5,
                    'amount_percentage_base': 'contract.wage',
                    'code': 'PF',
                    'category_id': cls.env.ref('hr_payroll.DED').id,
                }), (0, 0, {
                    'name': 'Meal Voucher',
                    'amount_select': 'fix',
                    'amount_fix': 10,
                    'quantity': "'WORK100' in worked_days and worked_days['WORK100'].number_of_days",
                    'code': 'MA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 16,
                }), (0, 0, {
                    'name': 'Conveyance Allowance',
                    'amount_select': 'fix',
                    'amount_fix': 800,
                    'code': 'CA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 10,
                }), (0, 0, {
                    'name': 'House Rent Allowance',
                    'amount_select': 'percentage',
                    'amount_percentage': 40,
                    'amount_percentage_base': 'contract.wage',
                    'code': 'HRA',
                    'category_id': cls.env.ref('hr_payroll.ALW').id,
                    'sequence': 5,
                })
            ],
            'type_id': cls.env['hr.payroll.structure.type'].create({'name': 'Employee', 'country_id': False}).id,
            'journal_id': salaries_journal.id,
        })

        cls.professional_tax_rule = cls.env['hr.salary.rule'].create({
            'name': 'Professional Tax',
            'amount_select': 'fix',
            'sequence': 150,
            'amount_fix': -200,
            'code': 'PT',
            'category_id': cls.env.ref('hr_payroll.DED').id,
            'struct_id': cls.hr_structure_softwaredeveloper.id,
        })

        cls.hr_structure_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Salary Structure Type',
            'struct_ids': [(4, cls.hr_structure_softwaredeveloper.id)],
            'default_struct_id': cls.hr_structure_softwaredeveloper.id,
        })

        cls.hr_contract_john = cls.env['hr.contract'].create({
            'date_end': fields.Date.to_string(datetime.now() + timedelta(days=365)),
            'date_start': date(2010, 1, 1),
            'name': 'Contract for John',
            'wage': 5000.0,
            'employee_id': cls.hr_employee_john.id,
            'structure_type_id': cls.hr_structure_type.id,
            'state': 'open',
        })

        cls.hr_payslip_john = cls.env['hr.payslip'].create({
            'employee_id': cls.hr_employee_john.id,
            'struct_id' : cls.hr_structure_softwaredeveloper.id,
            'contract_id': cls.hr_contract_john.id,
            'journal_id': cls.account_journal.id,
            'name': 'Test Payslip John',
            'number': 'PAYSLIPTEST01',
        })

        cls.hr_contract_mark = cls.env['hr.contract'].create({
            'date_end': fields.Date.to_string(datetime.now() + timedelta(days=365)),
            'date_start': date(2010, 1, 1),
            'name': 'Contract for Mark',
            'wage': 5000.0,
            'employee_id': cls.hr_employee_mark.id,
            'structure_type_id': cls.hr_structure_type.id,
            'state': 'open',
        })

        cls.hr_payslip_john.date_from = time.strftime('%Y-%m-01')
        # YTI Clean that brol
        cls.hr_payslip_john.date_to = str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10]

        cls.payslip_run = cls.env['hr.payslip.run'].create({
            'date_start': time.strftime('%Y-%m-01'),
            'date_end': str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10],
            'name': 'Payslip for Employee'
        })


@odoo.tests.tagged('post_install', '-at_install')
class TestHrPayrollAccount(TestHrPayrollAccountCommon):

    def test_00_hr_payslip_run(self):
        """ Checking the process of payslip run when you create payslip(s) in a payslip run and you validate the payslip run. """

        # I verify the payslip run is in draft state.
        self.assertEqual(self.payslip_run.state, 'draft', 'State not changed!')

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I confirm the payslip run.
        self.payslip_run.action_validate()

        # I verify the payslips is in done state.
        for slip in self.payslip_run.slip_ids:
            self.assertEqual(slip.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are created.
        for slip in self.payslip_run.slip_ids:
            self.assertTrue(slip.move_id, 'Accounting Entries has not been created!')

    def test_01_hr_payslip_run(self):
        """ Checking the process of payslip run when you create payslip in a payslip run and you validate the payslip(s). """

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I confirm all payslip(s) in the payslip run.
        self.payslip_run.slip_ids.action_payslip_done()

        # I verify the payslip(s) is in done state.
        for slip in self.payslip_run.slip_ids:
            self.assertEqual(slip.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are created.
        for slip in self.payslip_run.slip_ids:
            self.assertTrue(slip.move_id, 'Accounting Entries has not been created!')

    def test_02_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip in a payslip run and you cancel the payslip(s). """

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I confirm all payslip(s) in the payslip run.
        self.payslip_run.slip_ids.action_payslip_cancel()

        # I verify the payslip(s) is in cancel state.
        for slip in self.payslip_run.slip_ids:
            self.assertEqual(slip.state, 'cancel', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are not created.
        for slip in self.payslip_run.slip_ids:
            self.assertFalse(slip.move_id, 'Accounting Entries has been created!')

    def test_03_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip in a payslip run and you cancel a payslip and confirm another. """

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # Test only with payslip that were just generated. Remove the payslip from setup
        self.payslip_run.write({'slip_ids': [(3, self.hr_payslip_john.id)]})

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # I cancel one payslip and confirm another in the payslip run.
        payslip_1 = self.payslip_run.slip_ids[0]
        payslip_2 = self.payslip_run.slip_ids[1]
        payslip_1.action_payslip_cancel()
        payslip_2.action_payslip_done()

        # I verify the payslips' states.
        self.assertEqual(payslip_1.state, 'cancel', 'State not changed!')
        self.assertEqual(payslip_2.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are created or not.
        self.assertFalse(payslip_1.move_id, 'Accounting Entries has been created!')
        self.assertTrue(payslip_2.move_id, 'Accounting Entries has not been created!')

    def test_04_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip in a payslip run and you cancel a payslip and after you confirm the payslip run. """

        # I create a payslip employee.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.hr_employee_john.id), (4, self.hr_employee_mark.id)]
        })

        # I generate the payslip by clicking on Generate button wizard.
        payslip_employee.with_context(active_id=self.payslip_run.id).compute_sheet()

        # I verify if the payslip run has payslip(s).
        self.assertTrue(len(self.payslip_run.slip_ids) > 0, 'Payslip(s) not added!')

        # I verify the payslip run is in verify state.
        self.assertEqual(self.payslip_run.state, 'verify', 'State not changed!')

        # Storing the references to slip_ids[0] and slip_ids[1]
        # for later use, because the order of the One2many is not guaranteed
        slip0 = self.payslip_run.slip_ids[0]
        slip1 = self.payslip_run.slip_ids[1]

        # I cancel one payslip and after i confirm the payslip run.
        slip0.action_payslip_cancel()
        self.payslip_run.action_validate()

        # I verify the payslips' states.
        self.assertEqual(slip0.state, 'cancel', 'State not changed!')
        self.assertEqual(slip1.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.payslip_run.state, 'close', 'State not changed!')

        # I verify that the Accounting Entries are created or not.
        self.assertFalse(slip0.move_id, 'Accounting Entries has been created!')
        self.assertTrue(slip1.move_id, 'Accounting Entries has not been created!')

    def test_05_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip run from a payslip and you validate it. """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I create and i add the payslip run to the payslip.
        self.hr_payslip_john.payslip_run_id = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.hr_payslip_john.payslip_run_id.state, 'close', 'State not changed!')

        # I verify that the Accounting Entry is created.
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

    def test_06_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip run from a payslip and you validate the payslip run.  """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I create and i add the payslip run to the payslip.
        self.hr_payslip_john.payslip_run_id = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })
        self.hr_payslip_john.compute_sheet()

        # I validate the payslip run.
        self.hr_payslip_john.payslip_run_id.action_validate()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.hr_payslip_john.payslip_run_id.state, 'close', 'State not changed!')

        # I verify that the Accounting Entry is created.
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

    def test_07_hr_payslip(self):
        """ Checking the process of payslip run when you create payslip run from a payslip and you cancel it.  """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I create and i add the payslip run to the payslip.
        self.hr_payslip_john.payslip_run_id = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })

        # I cancel the payslip.
        self.hr_payslip_john.action_payslip_cancel()

        # I verify the payslip is in cancel state.
        self.assertEqual(self.hr_payslip_john.state, 'cancel', 'State not changed!')

        # I verify the payslip run is in close state.
        self.assertEqual(self.hr_payslip_john.payslip_run_id.state, 'close', 'State not changed!')

        # I verify that the Accounting Entry is not created.
        self.assertFalse(self.hr_payslip_john.move_id, 'Accounting entry has been created!')

    def test_08_hr_payslip(self):
        """ Checking the process of a payslip when you validate it and it has not a payslip run.  """

        # I verify if the payslip has not already a payslip run.
        self.assertFalse(self.hr_payslip_john.payslip_run_id, 'There is already a payslip run!')

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I verify that the Accounting Entry is created.
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

    def test_09_hr_payslip(self):
        """Checking if taxes are added on a payslip accounting entry when there is a default tax on the journal"""

        # Create a default tax for the account on the salary rule.
        tax_account = self.env['account.account'].create({
            'name': 'Rental Tax',
            'code': '777777',
            'account_type': 'asset_current',
        })
        hra_tax = self.env['account.tax'].create({
            'name': "hra_tax",
            'amount_type': 'percent',
            'amount': 10.0,
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'account_id': tax_account.id}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'factor_percent': 100, 'account_id': tax_account.id}),
            ],
        })

        # Create a account for the HRA salary rule.
        self.hra_account = self.env['account.account'].create({
            'name': 'House Rental',
            'code': '654321',
            'account_type': 'income',
            'tax_ids': [(4, hra_tax.id)]
        })

        # Assign the account to the salary rule and the rule to the hr structure.
        self.hra_rule.account_credit = self.hra_account
        self.hra_rule.account_debit = self.hra_account
        self.hr_structure_softwaredeveloper.rule_ids = [(4, self.hra_rule.id)]

        self.hr_payslip_john.compute_sheet()

        # Validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # Verify that the taxes are applied on hra move lines.
        for line in self.hr_payslip_john.move_id.line_ids:
            if line.account_id.id == self.hra_account.id:
                self.assertEqual(line.tax_ids, hra_tax, 'The account default tax is not added to move lines!')

    def test_payslip_refund(self):
        """ Checking if refunding a payslip creates the correct invoice lines """

        # Create an account for the HRA salary rule
        self.test_account = self.env['account.account'].create({
            'name': 'House Rental',
            'code': '654321',
            'account_type': 'income',
        })

        # Assign the account to the salary rule and the rule to the hr structure
        self.hra_rule.account_credit = self.test_account
        self.hra_rule.account_debit = self.test_account
        self.hr_structure_softwaredeveloper.rule_ids = [(4, self.hra_rule.id)]

        # Validate the payslip
        self.hr_payslip_john.compute_sheet()
        self.hr_payslip_john.action_payslip_done()

        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

        invoice_lines = self.hr_payslip_john.move_id.line_ids.sorted('amount_currency')

        # Verify that there are 2 invoice lines
        # 1. amount = -2000, credit = 2000, debit = 0
        # 2. amount = 2000, credit = 0, debit = 2000
        line_amount = self.hra_rule.amount_percentage / 100 * self.hr_payslip_john._get_contract_wage()

        self.assertEqual(len(invoice_lines), 2, 'There should be 2 invoice lines')

        self.assertEqual(invoice_lines[0].amount_currency, -line_amount)
        self.assertEqual(invoice_lines[0].credit, line_amount)
        self.assertEqual(invoice_lines[0].debit, 0)

        self.assertEqual(invoice_lines[1].amount_currency, line_amount)
        self.assertEqual(invoice_lines[1].credit, 0)
        self.assertEqual(invoice_lines[1].debit, line_amount)

        # Post the invoice
        self.hr_payslip_john.move_id.action_post()

        # Refund the payslip
        self.hr_payslip_john.refund_sheet()

        refund_slip = self.env['hr.payslip'].search([
            ('employee_id', '=', self.hr_employee_john.id),
            ('credit_note', '=', True)
        ])

        refund_slip.action_payslip_done()

        self.assertEqual(refund_slip.state, 'done', 'State not changed!')
        self.assertTrue(refund_slip.move_id, 'Accounting entry has not been created!')

        invoice_lines = refund_slip.move_id.line_ids

        # Check that there are 2 invoice lines, and they are the inverse of the original payslip
        # 1. amount = -2000, credit = 2000, debit = 0
        # 2. amount = 2000, credit = 0, debit = 2000
        line_amount = self.hra_rule.amount_percentage / 100 * self.hr_payslip_john._get_contract_wage()

        self.assertEqual(len(invoice_lines), 2, 'There should be 2 invoice lines')
        self.assertEqual(invoice_lines[0].amount_currency, -line_amount)
        self.assertEqual(invoice_lines[0].credit, line_amount)
        self.assertEqual(invoice_lines[0].debit, 0)

        self.assertEqual(invoice_lines[1].amount_currency, line_amount)
        self.assertEqual(invoice_lines[1].credit, 0)
        self.assertEqual(invoice_lines[1].debit, line_amount)

    def _test_bank_account_partner_payment_payslip(self, add_isr_bank):
        """ Check that the payment generated for Professionnal Tax is made to the correct bank account
            (previously, the selected account of the payment was always the employee bank account,
            whatever the partner specified in the payment)
        """
        tax_partner = self.env['res.partner'].create({
            'name': 'Regular Tax partner',
            'is_company': True,
        })
        tax_bank = self.env['res.bank'].create({'name': 'Belfius'})
        if add_isr_bank:
            isr_partner_bank = self.env['res.partner.bank'].create({
                'acc_number': 'IT77H400725028682A0R202P050',
                'partner_id': tax_partner.id,
                'bank_id': tax_bank.id,
                'allow_out_payment': True,
            })
        tax_debit_account = self.env['account.account'].create({
            'name': "Professional tax",
            'code': "020202",
            'account_type': "liability_payable",
            'reconcile': True,
        })
        salary_payable = self.env['account.account'].create({
            'name': 'Salary Payable',
            'code': '2300',
            'reconcile': True,
            'account_type': 'liability_payable',
        })
        self.env['hr.salary.rule'].create({
            'name': 'Net Salary',
            'amount_select': 'code',
            'amount_python_compute': 'result = categories["BASIC"] + categories["ALW"] + categories["DED"]',
            'code': 'NET',
            'category_id': self.env.ref('hr_payroll.NET').id,
            'sequence': 200,
            'account_credit': salary_payable.id,
            'struct_id': self.hr_structure_softwaredeveloper.id,
        })
        # Set necessary properties so that 'action_payslip_done' will create lines for the payslip
        self.professional_tax_rule.account_debit = tax_debit_account.id
        self.professional_tax_rule.partner_id = tax_partner.id

        self.hr_payslip_john.compute_sheet()
        self.hr_payslip_john.action_payslip_done()

        # 1. Debit for Salary Expense
        # 2. Credit for Salary Payable
        # 3. Credit for Professionnal Tax
        self.assertEqual(len(self.hr_payslip_john.move_id.line_ids), 3, "3 lines should've been created for John payslip !")

        self.hr_payslip_john.move_id.action_post()
        payment_register_wizard = Form.from_action(self.env, self.hr_payslip_john.action_register_payment())
        saved_form = payment_register_wizard.save()

        # Simulate calling `action_create_payments` method from `account.payment.register`
        payments = saved_form._create_payments()
        self.assertEqual(len(payments), 2, "2 payments should've been made here (one for each line except for the salary expense associated "
            "with the salary rule created in this test).")
        for payment in payments:
            matching_lines = self.hr_payslip_john.move_id.line_ids.filtered(
                lambda line: float_compare(abs(line.amount_currency), payment.amount, precision_digits=3) == 0)
            self.assertEqual(len(matching_lines), 1, "1 line should match the payment here.")

            if payment.partner_id == self.hr_payslip_john.employee_id.work_contact_id:
                self.assertEqual(payment.partner_bank_id.id, self.hr_payslip_john.employee_id.bank_account_id.id,
                    "As the partner of the payment is the employee of the payslip, the partner_bank_id of the payment should be "
                    f"the employee's bank account. Instead, we have the bank account of '{payment.partner_bank_id.partner_id.name}'.")
            else:
                if add_isr_bank:
                    self.assertEqual(payment.partner_bank_id.id, isr_partner_bank.partner_id.bank_ids[0].id, "As the partner of the payment is "
                        f"'{isr_partner_bank.partner_id.name}', the 'partner_bank_id' should've been set to the bank of '{isr_partner_bank.partner_id.name}' !")
                else:
                    self.assertFalse(payment.partner_bank_id.id, f"As the partner of the payment is '{tax_partner.name}', "
                        "the 'partner_bank_id' shouldn't be set because the partner has no bank account !")

    def test_bank_account_partner_payment_payslip_partner_with_bank_account(self):
        self._test_bank_account_partner_payment_payslip(True)

    def test_bank_account_partner_payment_payslip_partner_without_bank_account(self):
        self._test_bank_account_partner_payment_payslip(False)

    def test_payslip_cancel_1(self):
        """ Checking if canceling a payslip unlinks the draft associated entry """

        # Create an account for the HRA salary rule
        self.test_account = self.env['account.account'].create({
            'name': 'House Rental',
            'code': '654321',
            'account_type': 'income',
        })

        # Assign the account to the salary rule and the rule to the hr structure
        self.hra_rule.account_credit = self.test_account
        self.hra_rule.account_debit = self.test_account
        self.hr_structure_softwaredeveloper.rule_ids = [Command.link(self.hra_rule.id)]

        # Create accounting entry
        self.hr_payslip_john.compute_sheet()
        self.hr_payslip_john.action_payslip_done()

        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

        invoice = self.hr_payslip_john.move_id

        # Cancel the payslip
        self.hr_payslip_john.action_payslip_cancel()

        self.assertFalse(invoice.exists(), 'Invoice has not been deleted')
        self.assertFalse(self.hr_payslip_john.move_id, 'Accounting entry has not been deleted!')

    def test_payslip_cancel_2(self):
        """ Checking if canceling a payslip reverses the posted entry """

        self.hr_payslip_john.journal_id.restrict_mode_hash_table = True
        # Create an account for the HRA salary rule
        self.test_account = self.env['account.account'].create({
            'name': 'House Rental',
            'code': '654321',
            'account_type': 'income',
        })

        # Assign the account to the salary rule and the rule to the hr structure
        self.hra_rule.account_credit = self.test_account
        self.hra_rule.account_debit = self.test_account
        self.hr_structure_softwaredeveloper.rule_ids = [Command.link(self.hra_rule.id)]

        # Create accounting entry
        self.hr_payslip_john.compute_sheet()
        self.hr_payslip_john.action_payslip_done()

        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

        invoice = self.hr_payslip_john.move_id
        invoice.action_post()
        self.assertNotEqual(invoice.inalterable_hash, False)

        # Cancel the payslip: posted entry will be reversed
        self.hr_payslip_john.action_payslip_cancel()
        self.assertTrue(invoice.exists(), 'Invoice has been deleted')

        line_amount = self.hra_rule.amount_percentage / 100 * self.hr_payslip_john._get_contract_wage()

        reverse_invoice = self.env['account.move.line'].search([
            ('amount_currency', '=', line_amount),
            ('move_id', '!=', invoice.id),
        ])
        self.assertTrue(reverse_invoice, 'Reverse move not created')

    def test_payslip_paid_create_journal_entry(self):
        """ Check that you cannot create a journal entry for a paid payslip """

        # I compute the payslip sheet.
        self.hr_payslip_john.compute_sheet()

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I mark the payslip as paid.
        self.hr_payslip_john.action_payslip_paid()

        # I verify that an error is thrown if we try to recreate a journal entry on paid payslip.
        self.assertRaises(ValidationError, self.hr_payslip_john.action_payslip_done)
