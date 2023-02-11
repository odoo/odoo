# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged, Form
from odoo.tools.misc import formatLang
from odoo import fields


@tagged('-at_install', 'post_install')
class TestExpenses(TestExpenseCommon):

    def test_expense_sheet_payment_state(self):
        ''' Test expense sheet payment states when partially paid, in payment and paid. '''

        def get_payment(expense_sheet, amount):
            ctx = {'active_model': 'account.move', 'active_ids': expense_sheet.account_move_id.ids}
            payment_register = self.env['account.payment.register'].with_context(**ctx).create({
                'amount': amount,
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_method_line_id': self.inbound_payment_method_line.id,
            })
            return payment_register._create_payments()

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'accounting_date': '2021-01-01',
            'expense_line_ids': [(0, 0, {
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'unit_amount': 350.00,
            })]
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        payment = get_payment(expense_sheet, 100.0)
        liquidity_lines1 = payment._seek_for_lines()[0]

        self.assertEqual(expense_sheet.payment_state, 'partial', 'payment_state should be partial')

        payment = get_payment(expense_sheet, 250.0)
        liquidity_lines2 = payment._seek_for_lines()[0]

        in_payment_state = expense_sheet.account_move_id._get_invoice_in_payment_state()
        self.assertEqual(expense_sheet.payment_state, in_payment_state, 'payment_state should be ' + in_payment_state)

        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'journal_id': self.company_data['default_journal_bank'].id,
            'line_ids': [
                (0, 0, {
                    'payment_ref': 'pay_ref',
                    'amount': -350.0,
                    'partner_id': self.expense_employee.address_home_id.id,
                }),
            ],
        })
        statement.button_post()
        statement.line_ids.reconcile([{'id': liquidity_lines1.id}, {'id': liquidity_lines2.id}])

        self.assertEqual(expense_sheet.payment_state, 'paid', 'payment_state should be paid')

    def test_expense_values(self):
        """ Checking accounting move entries and analytic entries when submitting expense """

        # The expense employee is able to a create an expense sheet.
        # The total should be 1500.0 because:
        # - first line: 1000.0 (unit amount), 130.43 (tax). But taxes are included in total thus - 1000
        # - second line: (1500.0 (unit amount), 195.652 (tax)) - 65.22 (tax in company currency). total 1500.0 * 1/3 (rate) = 500

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                (0, 0, {
                    # Expense without foreign currency.
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 1000.0,
                    'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)],
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                }),
                (0, 0, {
                    # Expense with foreign currency (rate 1:3).
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_b.id,
                    'unit_amount': 1500.0,
                    'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)],
                    'analytic_account_id': self.analytic_account_2.id,
                    'currency_id': self.currency_data['currency'].id,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        # Check expense sheet values.
        self.assertRecordValues(expense_sheet, [{'state': 'draft', 'total_amount': 1500.0}])

        expense_sheet.action_submit_sheet()
        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        # Check expense sheet journal entry values.
        self.assertRecordValues(expense_sheet.account_move_id.line_ids.sorted('balance'), [
            # Receivable line (company currency):
            {
                'debit': 0.0,
                'credit': 1000.0,
                'amount_currency': -1000.0,
                'account_id': self.company_data['default_account_payable'].id,
                'product_id': False,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': False,
                'analytic_account_id': False,
            },
            # Receivable line (foreign currency):
            {
                'debit': 0.0,
                'credit': 750,
                'amount_currency': -1500.0,
                'account_id': self.company_data['default_account_payable'].id,
                'product_id': False,
                'currency_id': self.currency_data['currency'].id,
                'tax_line_id': False,
                'analytic_account_id': False,
            },
            # Tax line (foreign currency):
            {
                'debit': 97.83,
                'credit': 0.0,
                'amount_currency': 195.652,
                'account_id': self.company_data['default_account_tax_purchase'].id,
                'product_id': False,
                'currency_id': self.currency_data['currency'].id,
                'tax_line_id': self.company_data['default_tax_purchase'].id,
                'analytic_account_id': False,
            },
            # Tax line (company currency):
            {
                'debit': 130.43,
                'credit': 0.0,
                'amount_currency': 130.43,
                'account_id': self.company_data['default_account_tax_purchase'].id,
                'product_id': False,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': self.company_data['default_tax_purchase'].id,
                'analytic_account_id': False,
            },
            # Product line (foreign currency):
            {
                'debit': 652.17,
                'credit': 0.0,
                'amount_currency': 1304.348, # untaxed amount
                'account_id': self.company_data['default_account_expense'].id,
                'product_id': self.product_b.id,
                'currency_id': self.currency_data['currency'].id,
                'tax_line_id': False,
                'analytic_account_id': self.analytic_account_2.id,
            },
            # Product line (company currency):
            {
                'debit': 869.57,
                'credit': 0.0,
                'amount_currency': 869.57,
                'account_id': self.company_data['default_account_expense'].id,
                'product_id': self.product_a.id,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': False,
                'analytic_account_id': self.analytic_account_1.id,
            },
        ])

        # Check expense analytic lines.
        self.assertRecordValues(expense_sheet.account_move_id.line_ids.analytic_line_ids.sorted('amount'), [
            {
                'amount': -869.57,
                'date': fields.Date.from_string('2017-01-01'),
                'account_id': self.analytic_account_1.id,
                'currency_id': self.company_data['currency'].id,
            },
            {
                'amount': -652.17,
                'date': fields.Date.from_string('2017-01-01'),
                'account_id': self.analytic_account_2.id,
                'currency_id': self.company_data['currency'].id,
            },
        ])

    def test_account_entry_multi_currency(self):
        """ Checking accounting move entries and analytic entries when submitting expense. With
            multi-currency. And taxes. """

        # Clean-up the rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.env.ref('base.USD').id, self.env.company.id])
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.company.id,
            'rate': 2.0,
            'name': '2010-01-01',
        })

        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for Dick Tracy',
            'employee_id': self.expense_employee.id,
        })
        tax = self.env['account.tax'].create({
            'name': 'Expense 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
        })
        self.env['hr.expense'].create({
            'name': 'Choucroute Saucisse',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'unit_amount': 700.00,
            'tax_ids': [(6, 0, tax.ids)],
            'sheet_id': expense.id,
            'analytic_account_id': self.analytic_account_1.id,
            'currency_id': self.env.ref('base.EUR').id,
        })

        # State should default to draft
        self.assertEqual(expense.state, 'draft', 'Expense should be created in Draft state')
        # Submitted to Manager
        expense.action_submit_sheet()
        self.assertEqual(expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        expense.approve_expense_sheets()
        self.assertEqual(expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        expense.action_sheet_move_create()
        self.assertEqual(expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.account_move_id.id, 'Expense Journal Entry is not created')

        # Should get this result [(0.0, 350.0, -700.0), (318.18, 0.0, 636.36), (31.82, 0.0, 63.64)]
        for line in expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEqual(line.credit, 350.0)
                self.assertAlmostEqual(line.amount_currency, -700.0)
                self.assertEqual(len(line.analytic_line_ids), 0, "The credit move line should not have analytic lines")
                self.assertFalse(line.product_id, "Product of credit move line should be false")
            else:
                if not line.tax_line_id == tax:
                    self.assertAlmostEqual(line.debit, 318.18)
                    self.assertAlmostEqual(line.amount_currency, 636.36)
                    self.assertEqual(len(line.analytic_line_ids), 1, "The debit move line should have 1 analytic lines")
                    self.assertEqual(line.product_id, self.product_a, "Product of debit move line should be the one from the expense")
                else:
                    self.assertEqual(line.tax_base_amount, 318.18)
                    self.assertAlmostEqual(line.debit, 31.82)
                    self.assertAlmostEqual(line.amount_currency, 63.64)
                    self.assertEqual(len(line.analytic_line_ids), 0, "The tax move line should not have analytic lines")
                    self.assertFalse(line.product_id, "Product of tax move line should be false")

    def test_expenses_with_tax_and_lockdate(self):
        ''' Test creating a journal entry for multiple expenses using taxes. A lock date is set in order to trigger
        the recomputation of the taxes base amount.
        '''
        self.env.company.tax_lock_date = '2020-02-01'

        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01'
        })

        for i in range(2):
            expense_line = self.env['hr.expense'].create({
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'unit_amount': 350.00,
                'tax_ids': [(6, 0, [self.tax_purchase_a.id])],
                'sheet_id': expense.id,
                'analytic_account_id': self.analytic_account_1.id,
            })
            expense_line._onchange_product_id_date_account_id()

        expense.action_submit_sheet()
        expense.approve_expense_sheets()

        # Assert not "Cannot create unbalanced journal entry" error.
        expense.action_sheet_move_create()

    def test_reconcile_payment(self):
        tax = self.env['account.tax'].create({
            'name': 'tax abc',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 15,
            'price_include': False,
            'include_base_amount': False,
            'tax_exigibility': 'on_payment'
        })
        current_assets_type = self.env.ref('account.data_account_type_current_assets')
        company = self.env.company.id
        tax.cash_basis_transition_account_id = self.env['account.account'].create({
            'name': "test",
            'code': 999991,
            'reconcile': True,
            'user_type_id': current_assets_type.id,
            'company_id': company,
        }).id

        sheet = self.env['hr.expense.sheet'].create({
            'company_id': company,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet',
            'expense_line_ids': [
                (0, 0, {
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 10.0,
                    'employee_id': self.expense_employee.id,
                    'tax_ids': tax
                }),
                (0, 0, {
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 1.0,
                    'employee_id': self.expense_employee.id,
                    'tax_ids': tax
                }),
            ],
        })


        #actions
        sheet.action_submit_sheet()
        sheet.approve_expense_sheets()
        sheet.action_sheet_move_create()
        action_data = sheet.action_register_payment()
        wizard = Form(self.env['account.payment.register'].with_context(action_data['context'])).save()
        action = wizard.action_create_payments()
        self.assertEqual(sheet.state, 'done', 'all account.move.line linked to expenses must be reconciled after payment')
        
        move = self.env['account.payment'].browse(action['res_id']).move_id
        move.button_cancel()
        self.assertEqual(sheet.state, 'cancel', 'Sheet state must be cancel when the payment linked to that sheet is canceled')

    def test_expense_amount_total_signed_compute(self):
        sheet = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet',
            'expense_line_ids': [
                (0, 0, {
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 10.0,
                    'employee_id': self.expense_employee.id
                }),
            ],
        })


        #actions
        sheet.action_submit_sheet()
        sheet.approve_expense_sheets()
        sheet.action_sheet_move_create()
        action_data = sheet.action_register_payment()
        wizard = Form(self.env['account.payment.register'].with_context(action_data['context'])).save()
        action = wizard.action_create_payments()

        move = self.env['account.payment'].browse(action['res_id']).move_id
        self.assertEqual(move.amount_total_signed, 10.0, 'The total amount of the payment move is not correct')

    def test_print_expense_check(self):
        """
        Test the check content when printing a check
        that comes from an expense
        """
        sheet = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet',
            'expense_line_ids': [
                (0, 0, {
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 10.0,
                    'employee_id': self.expense_employee.id,
                }),
                (0, 0, {
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 1.0,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        #actions
        sheet.action_submit_sheet()
        sheet.approve_expense_sheets()
        sheet.action_sheet_move_create()
        action_data = sheet.action_register_payment()
        payment_method_line = self.env.company.bank_journal_ids.outbound_payment_method_line_ids.filtered(lambda m: m.code == 'check_printing')
        with Form(self.env[action_data['res_model']].with_context(action_data['context'])) as wiz_form:
            wiz_form.payment_method_line_id = payment_method_line
        wizard = wiz_form.save()
        action = wizard.action_create_payments()
        self.assertEqual(sheet.state, 'done', 'all account.move.line linked to expenses must be reconciled after payment')

        payment = self.env[action['res_model']].browse(action['res_id'])
        pages = payment._check_get_pages()
        stub_line = pages[0]['stub_lines'][:1]
        self.assertTrue(stub_line)
        move = self.env[action_data['context']['active_model']].browse(action_data['context']['active_ids'])
        self.assertDictEqual(stub_line[0], {
            'due_date': '',
            'number': ' - '.join([move.name, move.ref] if move.ref else [move.name]),
            'amount_total': formatLang(self.env, 11.0, currency_obj=self.env.company.currency_id),
            'amount_residual': '-',
            'amount_paid': formatLang(self.env, 11.0, currency_obj=self.env.company.currency_id),
            'currency': self.env.company.currency_id
        })
