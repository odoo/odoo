# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged, Form
from odoo.tools.misc import formatLang
from odoo import fields, Command
from odoo.exceptions import UserError


@tagged('-at_install', 'post_install')
class TestExpenses(TestExpenseCommon):

    def test_expense_sheet_changing_employee(self):
        """ Test changing an employee on the expense that is linked with the sheet.
            - In case sheet has only one expense linked with it, than changing an employee
            on expense should trigger changing an employee on the sheet itself.
            - In case sheet has more than one expense linked with it, than changing an employee
            on one of the expenses, should cause unlinking the expense from the sheet."""

        employee = self.env['hr.employee'].create({
            'name': 'Gabriel Iglesias',
        })

        expense1 = self.env['hr.expense'].create({
            'name': 'Dinner with client - Expenses',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount': 350.00,
        })

        expense2 = self.env['hr.expense'].create({
            'name': 'Team building at Huy',
            'employee_id': employee.id,
            'product_id': self.product_c.id,
            'total_amount': 2500.00,
        })

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for Jannette',
            'employee_id': self.expense_employee.id,
            'expense_line_ids': expense1,
        })

        expense1.employee_id = employee
        self.assertEqual(expense_sheet.employee_id, employee, 'Employee should have changed on the sheet')

        expense_sheet.expense_line_ids |= expense2
        expense2.employee_id = self.expense_employee.id
        self.assertEqual(expense2.sheet_id.id, False, 'Sheet should be unlinked from the expense')

    def test_expense_sheet_paid_employee(self):
        ''' Test expense sheet paid by employee flow'''

        def get_payment(expense_sheet, amount):
            ctx = {'active_model': 'account.move', 'active_ids': expense_sheet.account_move_ids.ids}
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
                'product_id': self.product_c.id,
                'total_amount': 350.00,
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            })]
        })

        expense_sheet.action_submit_sheet()
        self.assertEqual(expense_sheet.state, 'submit', 'sheet should be submitted')

        expense_sheet.action_approve_expense_sheets()
        self.assertEqual(expense_sheet.state, 'approve', 'sheet should be aproved')

        expense_sheet.action_sheet_move_create()
        self.assertEqual(expense_sheet.state, 'post', 'sheet should be posted')

        move = expense_sheet.account_move_ids

        self.assertRecordValues(move.line_ids, [
            {'debit': 304.35, 'credit': 0.0, 'reconciled': False, },
            {'debit': 45.65, 'credit': 0.0, 'reconciled': False},
            {'debit': 0.0, 'credit': 350, 'reconciled': False},
        ])

        expense_sheet.action_reset_expense_sheets()
        self.assertEqual(expense_sheet.state, 'draft', 'sheet should be reverted to draft')

        reverse_move = self.env['account.move'].search([('reversed_entry_id', '=', move.id)])
        self.assertFalse(expense_sheet.account_move_ids)
        self.assertEqual(move.payment_state, 'reversed', 'vendor bill should be reversed')
        self.assertTrue(350 == expense_sheet.total_amount == move.amount_total == reverse_move.amount_total, 'taxes properly included in price')

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        payment_1 = get_payment(expense_sheet, 100.0)
        liquidity_lines1 = payment_1._seek_for_lines()[0]

        self.assertEqual(expense_sheet.payment_state, 'partial', 'payment_state should be partial')

        payment_2 = get_payment(expense_sheet, 250.0)
        liquidity_lines2 = payment_2._seek_for_lines()[0]

        in_payment_state = expense_sheet.account_move_ids._get_invoice_in_payment_state()
        self.assertEqual(expense_sheet.payment_state, in_payment_state, 'payment_state should be ' + in_payment_state)
        self.assertEqual(expense_sheet.state, 'done', 'sheet should be marked as done')

        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ref': 'pay_ref',
            'amount': -350.0,
            'partner_id': self.expense_employee.work_contact_id.id,
        })

        # Reconcile without the bank reconciliation widget since the widget is in enterprise.
        _st_liquidity_lines, st_suspense_lines, _st_other_lines = statement_line\
            .with_context(skip_account_move_synchronization=True)\
            ._seek_for_lines()
        st_suspense_lines.account_id = liquidity_lines1.account_id
        (st_suspense_lines + liquidity_lines1 + liquidity_lines2).reconcile()

        self.assertEqual(expense_sheet.payment_state, 'paid', 'payment_state should be paid')
        self.assertEqual(expense_sheet.state, 'done', 'sheet should be marked as done')

        payment_1.action_draft()
        payment_2.action_draft()

        self.assertEqual(expense_sheet.state, 'post', 'sheet should be reverted to posted')
        self.assertEqual(expense_sheet.payment_state, 'not_paid', 'payment_state should be not_paid')

    def test_expense_sheet_paid_company(self):
        ''' Test expense sheet paid by company flow '''

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'accounting_date': '2021-01-01',
            'payment_method_line_id': self.outbound_payment_method_line.id,
            'expense_line_ids': [(0, 0, {
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 350.00,
                'payment_mode': 'company_account',
            })]
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        move = expense_sheet.account_move_ids

        self.assertEqual(expense_sheet.state, 'done', 'sheet should be marked as done')
        self.assertTrue(350 == expense_sheet.total_amount == move.amount_total == move.payment_id.amount)

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
            'expense_line_ids': [
                (0, 0, {
                    # Expense without foreign currency.
                    'name': 'expense_company_currency',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'quantity': 1.25,
                    'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)],
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                }),
                (0, 0, {
                    # Expense with foreign currency (rate 1:3).
                    'name': 'expense_foreign_currency',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id, # product with no cost, else not possible to enter amount in different currency
                    'total_amount': 1500.0,
                    'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)],
                    'analytic_distribution': {self.analytic_account_2.id: 100},
                    'currency_id': self.currency_data['currency'].id,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        self.assertRecordValues(expense_sheet, [{'state': 'draft', 'total_amount': 1500.0}])

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        # Check expense sheet journal entry values.
        self.assertRecordValues(expense_sheet.account_move_ids.line_ids.sorted('balance'), [
            # Receivable line (company currency):
            {
                'debit': 0.0,
                'credit': 1500.0,
                'amount_currency': -1500.0,
                'account_id': self.company_data['default_account_payable'].id,
                'product_id': False,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': False,
                'analytic_distribution': False,
            },
            # Tax line (foreign currency):
            {
                'debit': 65.22,
                'credit': 0.0,
                'amount_currency': 65.22,
                'account_id': self.company_data['default_account_tax_purchase'].id,
                'product_id': False,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': self.company_data['default_tax_purchase'].id,
                'analytic_distribution': False,
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
                'analytic_distribution': False,
            },
            # Product line (foreign currency):
            {
                'debit': 434.78, # 1500 * 1:3 (rate) / 1.15 (incl. tax)
                'credit': 0.0,
                'amount_currency': 434.78, # untaxed amount
                'account_id': self.product_c.property_account_expense_id.id,
                'product_id': self.product_c.id,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': False,
                'analytic_distribution': {str(self.analytic_account_2.id): 100},
            },
            # Product line (company currency):
            {
                'debit': 869.57, # 1000 / 1.15 (incl. tax)
                'credit': 0.0,
                'amount_currency': 869.57,
                'account_id': self.company_data['default_account_expense'].id,
                'product_id': self.product_a.id,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': False,
                'analytic_distribution': {str(self.analytic_account_1.id): 100},
            },
        ])

        # Check expense analytic lines.
        self.assertRecordValues(expense_sheet.account_move_ids.line_ids.analytic_line_ids.sorted('amount'), [
            {
                'amount': -869.57,
                'date': fields.Date.from_string('2016-01-01'),
                'account_id': self.analytic_account_1.id,
                'currency_id': self.company_data['currency'].id,
            },
            {
                'amount': -434.78,
                'date': fields.Date.from_string('2016-01-01'),
                'account_id': self.analytic_account_2.id,
                'currency_id': self.company_data['currency'].id,
            },
        ])

    def test_expense_company_account(self):
        """ Create an expense with payment mode 'Company' and post it (it should not fail) """
        with Form(self.env['hr.expense']) as expense_form:
            expense_form.name = 'Company expense'
            expense_form.date = '2022-11-17'
            expense_form.total_amount = 1000.0
            expense_form.payment_mode = 'company_account'
            expense_form.employee_id = self.expense_employee
            expense_form.product_id = self.product_a
            expense = expense_form.save()

        with Form(self.env['hr.expense.sheet']) as expense_sheet_form:
            # Use same values that will be used by action_submit_expenses
            expense_sheet_form.employee_id = expense.employee_id
            expense_sheet_form.name = expense.name
            expense_sheet_form.expense_line_ids.add(expense)
            expense_sheet_form.payment_method_line_id = self.outbound_payment_method_line
            expense_sheet = expense_sheet_form.save()

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

    def test_account_entry_multi_currency(self):
        """ Checking accounting move entries and analytic entries when submitting expense. With
            multi-currency. And taxes. """
        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for Dick Tracy',
            'employee_id': self.expense_employee.id,
        })
        tax_account = self.env['account.account'].search([('account_type', '=', 'liability_current')], limit=1)
        tax = self.env['account.tax'].create({
            'name': 'Tax Expense 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
            'repartition_line_ids': [
                Command.create({'document_type': 'invoice', 'repartition_type': 'base'}),
                Command.create({'document_type': 'invoice', 'repartition_type': 'tax', 'account_id': tax_account.id}),
                Command.create({'document_type': 'refund', 'repartition_type': 'base'}),
                Command.create({'document_type': 'refund', 'repartition_type': 'tax', 'account_id': tax_account.id}),
            ]
        })
        self.env['hr.expense'].create({
            'name': 'Choucroute Saucisse',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount': 700.0,
            'tax_ids': [(6, 0, tax.ids)],
            'sheet_id': expense.id,
            'analytic_distribution': {self.analytic_account_1.id: 100},
            'currency_id': self.currency_data['currency'].id, # rate is 1:2
        })

        # State should default to draft
        self.assertEqual(expense.state, 'draft', 'Expense should be created in Draft state')
        # Submitted to Manager
        expense.action_submit_sheet()
        self.assertEqual(expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        expense.action_approve_expense_sheets()
        self.assertEqual(expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        expense.action_sheet_move_create()
        self.assertEqual(expense.state, 'post', 'Expense is not in Waiting Payment state')
        # Should get this result [(0.0, 350.0, -700.0), (318.18, 0.0, 636.36), (31.82, 0.0, 63.64)]
        analytic_line = expense.account_move_ids.line_ids.analytic_line_ids
        self.assertEqual(len(analytic_line), 1)

        # Expenses paid by the employee are always translated in company currency
        self.assertInvoiceValues(expense.account_move_ids, [
            {
                'balance': 318.18, # 700 * 1:2 (rate) / 1.1 (incl. tax)
                'amount_currency': 318.18,
                'product_id': self.product_c.id,
                'price_unit': 350.0,
                'price_subtotal': 318.18,
                'price_total': 350.0,
                'analytic_line_ids': analytic_line.ids,
            }, {
                'balance': 31.82,
                'amount_currency': 31.82,
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'analytic_line_ids': [],
            }, {
                'balance': -350.0,
                'amount_currency': -350.0,
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'analytic_line_ids': [],
            },
        ], {
            'amount_total': 350.0,
        })

    def test_account_entry_multi_currency_company_account(self):
        """ Checking accounting payment entry when payment_mode is 'Company'. With multi-currency."""
        expense = self.env['hr.expense'].create({
            'name': 'Company expense',
            'date': '2022-11-17',
            'total_amount': 1000.0,
            'payment_mode': 'company_account',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'currency_id': self.currency_data['currency'].id,  # rate is 1:2
        })

        foreign_bank_journal = self.company_data['default_journal_bank'].copy()
        foreign_bank_journal_account = foreign_bank_journal.default_account_id.copy()
        foreign_bank_journal_account.currency_id = self.currency_data['currency'].id
        foreign_bank_journal.write({
            'currency_id': self.currency_data['currency'].id,
            'default_account_id': foreign_bank_journal_account.id
        })
        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': "test_account_entry_multi_currency_own_account",
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01',
            'payment_method_line_id': foreign_bank_journal.outbound_payment_method_line_ids[0].id,
            'expense_line_ids': [Command.set(expense.ids)],
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()
        self.assertRecordValues(expense_sheet.account_move_ids.payment_id, [{
            'currency_id': self.currency_data['currency'].id,
        }])
        self.assertRecordValues(expense_sheet.account_move_ids.line_ids, [
            {'currency_id': self.currency_data['currency'].id},
            {'currency_id': self.currency_data['currency'].id},
            {'currency_id': self.currency_data['currency'].id},
            {'currency_id': self.currency_data['currency'].id},
        ])

    def test_account_entry_multi_currency_own_account(self):
        """ Checking accounting payment entry when payment_mode is 'Company'. With multi-currency."""
        expense = self.env['hr.expense'].create({
            'name': 'Company expense',
            'date': '2022-11-17',
            'payment_mode': 'own_account',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'currency_id': self.currency_data['currency'].id, # rate is 1:2
        })

        foreign_sale_journal = self.company_data['default_journal_sale'].copy()
        foreign_sale_journal.currency_id = self.currency_data['currency'].id

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': "test_account_entry_multi_currency_own_account",
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01',
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.set(expense.ids)],
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()
        self.assertRecordValues(expense_sheet.account_move_ids, [{
            'currency_id': expense_sheet.company_id.currency_id.id,
        }])
        self.assertRecordValues(expense_sheet.account_move_ids.line_ids, [
            {'currency_id': expense_sheet.company_id.currency_id.id},
            {'currency_id': expense_sheet.company_id.currency_id.id},
            {'currency_id': expense_sheet.company_id.currency_id.id},
        ])

    def test_multicurrencies_rounding_consistency(self):
        # pylint: disable=bad-whitespace
        foreign_currency = self.env['res.currency'].create({
            'name': 'Exposure',
            'symbol': ' ',
            'rounding': 0.01,
            'position': 'after',
            'currency_unit_label': 'Nothing',
            'currency_subunit_label': 'Smaller Nothing',
        })
        self.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 1/0.148431,
            'currency_id': foreign_currency.id,
            'company_id': self.company_data['company'].id,
        })
        foreign_sale_journal = self.company_data['default_journal_sale'].copy()
        foreign_sale_journal.currency_id = foreign_currency.id
        tax = self.env['account.tax'].create({
            'name': 'Tax Expense 15%',
            'amount': 15,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
        })
        taxes = tax + tax.copy()

        expense_sheet_own_1_tax = self.env['hr.expense.sheet'].create({
            'name': "own expense 1 tax",
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01',
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.create({
                'name': 'Own expense',
                'date': '2022-11-16',
                'payment_mode': 'own_account',
                'total_amount': 100,
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'currency_id': foreign_currency.id,  # rate is 1:0.148431
                'tax_ids': [Command.set(tax.ids)],
            })],
        })
        expense_sheet_own_2_tax = self.env['hr.expense.sheet'].create({
            'name': "own expense 2 taxes",
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01',
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.create({
                'name': 'Own expense',
                'date': '2022-11-17',
                'payment_mode': 'own_account',
                'total_amount': 100,
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'currency_id': foreign_currency.id,  # rate is 1:0.148431
                'tax_ids': [Command.set(taxes.ids)],
            })],
        })
        expense_sheet_company_1_tax = self.env['hr.expense.sheet'].create({
            'name': "company expense 1 taxes",
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01',
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.create({
                'name': 'Company expense',
                'date': '2022-11-18',
                'payment_mode': 'company_account',
                'total_amount': 100,
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'currency_id': foreign_currency.id,  # rate is 1:0.148431
                'tax_ids': [Command.set(tax.ids)],
            })],
        })
        expense_sheet_company_2_tax = self.env['hr.expense.sheet'].create({
            'name': "company expense 2 taxes",
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01',
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.create({
                'name': 'Company expense',
                'date': '2022-11-19',
                'payment_mode': 'company_account',
                'total_amount': 100,
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'currency_id': foreign_currency.id,  # rate is 1:0.148431
                'tax_ids': [Command.set(taxes.ids)],
            })],
        })
        sheets = expense_sheet_own_1_tax + expense_sheet_own_2_tax + expense_sheet_company_1_tax + expense_sheet_company_2_tax
        self.assertRecordValues(sheets.expense_line_ids, [
            {'untaxed_amount':  86.96, 'total_amount': 100.00, 'total_amount_company': 14.84, 'amount_tax': 13.04, 'amount_tax_company': 1.94},
            {'untaxed_amount':  76.92, 'total_amount': 100.00, 'total_amount_company': 14.84, 'amount_tax': 23.08, 'amount_tax_company': 3.42},
            {'untaxed_amount':  86.96, 'total_amount': 100.00, 'total_amount_company': 14.84, 'amount_tax': 13.04, 'amount_tax_company': 1.94},
            {'untaxed_amount':  76.92, 'total_amount': 100.00, 'total_amount_company': 14.84, 'amount_tax': 23.08, 'amount_tax_company': 3.42},
        ])

        sheets.action_submit_sheet()
        sheets.action_approve_expense_sheets()
        sheets.action_sheet_move_create()
        self.assertRecordValues(expense_sheet_own_1_tax.account_move_ids.line_ids, [
            {'balance':  12.90, 'amount_currency':  12.90, 'currency_id': self.company_data['currency'].id},
            {'balance':   1.94, 'amount_currency':   1.94, 'currency_id': self.company_data['currency'].id},
            {'balance': -14.84, 'amount_currency': -14.84, 'currency_id': self.company_data['currency'].id},
        ])

        self.assertRecordValues(expense_sheet_own_2_tax.account_move_ids.line_ids, [
            {'balance':  11.42, 'amount_currency':  11.42, 'currency_id': self.company_data['currency'].id},
            {'balance':   1.71, 'amount_currency':   1.71, 'currency_id': self.company_data['currency'].id},
            {'balance':   1.71, 'amount_currency':   1.71, 'currency_id': self.company_data['currency'].id},  #  == 3.42 amount_tax_company
            {'balance': -14.84, 'amount_currency': -14.84, 'currency_id': self.company_data['currency'].id},
        ])

        self.assertRecordValues(expense_sheet_company_1_tax.account_move_ids.line_ids, [
            {'balance':  12.90, 'amount_currency':   86.96, 'currency_id': foreign_currency.id},
            {'balance':   1.94, 'amount_currency':   13.04, 'currency_id': foreign_currency.id},
            {'balance': -14.84, 'amount_currency': -100.00, 'currency_id': foreign_currency.id},
        ])

        self.assertRecordValues(expense_sheet_company_2_tax.account_move_ids.line_ids, [
            {'balance':  11.42, 'amount_currency':   76.92, 'currency_id': foreign_currency.id},
            {'balance':   1.71, 'amount_currency':   11.54, 'currency_id': foreign_currency.id},  #  == 3.42 amount_tax_company & 23.08 amount_tax
            {'balance':   1.71, 'amount_currency':   11.54, 'currency_id': foreign_currency.id},  # One cent more in currency due to rounding
            {'balance': -14.84, 'amount_currency': -100.00, 'currency_id': foreign_currency.id},
        ])


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

        for _i in range(2):
            self.env['hr.expense'].create({
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 350.00,
                'tax_ids': [(6, 0, [self.tax_purchase_a.id])],
                'sheet_id': expense.id,
                'analytic_distribution': {str(self.analytic_account_1.id): 100},
            })

        expense.action_submit_sheet()
        expense.action_approve_expense_sheets()

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
        company = self.env.company.id
        tax.cash_basis_transition_account_id = self.env['account.account'].create({
            'name': "test",
            'code': 999991,
            'reconcile': True,
            'account_type': 'asset_current',
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
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'employee_id': self.expense_employee.id,
                    'tax_ids': tax
                }),
                (0, 0, {
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 1.0,
                    'employee_id': self.expense_employee.id,
                    'tax_ids': tax
                }),
            ],
        })


        #actions
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_create()
        action_data = sheet.action_register_payment()
        wizard = Form(self.env['account.payment.register'].with_context(action_data['context'])).save()
        action = wizard.action_create_payments()
        self.assertEqual(sheet.state, 'done', 'all account.move.line linked to expenses must be reconciled after payment')

    def test_expense_amount_total_signed_compute(self):
        sheet = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet',
            'expense_line_ids': [
                (0, 0, {
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'employee_id': self.expense_employee.id
                }),
            ],
        })

        #actions
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_create()
        action_data = sheet.action_register_payment()
        wizard = Form(self.env['account.payment.register'].with_context(action_data['context'])).save()
        action = wizard.action_create_payments()

        move = self.env['account.payment'].browse(action['res_id']).move_id
        self.assertEqual(move.amount_total_signed, 10.0, 'The total amount of the payment move is not correct')

    def test_form_defaults_from_product(self):
        """
        As soon as you set a product, the expense name, uom, taxes and account are set
        according to the product.
        """
        # Disable multi-uom
        self.env.ref('base.group_user').implied_ids -= self.env.ref('uom.group_uom')
        self.expense_user_employee.groups_id -= self.env.ref('uom.group_uom')

        # Use the expense employee
        Expense = self.env['hr.expense'].with_user(self.expense_user_employee)

        # Make sure the multi-uom is correctly disabled for the user creating the expense
        self.assertFalse(Expense.env.user.has_group('uom.group_uom'))

        # Use a product not using the default uom "Unit(s)"
        product = Expense.env.ref('hr_expense.expense_product_mileage')

        expense_form = Form(Expense)
        expense_form.product_id = product
        expense = expense_form.save()
        self.assertEqual(expense.name, product.display_name)
        self.assertEqual(expense.product_uom_id, product.uom_id)
        self.assertEqual(expense.tax_ids, product.supplier_taxes_id)
        self.assertEqual(expense.account_id, product._get_product_accounts()['expense'])

    def test_expense_account(self):
        """ Checking accounting move entries for the accounts set on the expenses """

        account_expense_1 = self.env['account.account'].create({
            'code': '610010',
            'name': 'Expense Account 1'
        })
        account_expense_2 = self.env['account.account'].create({
            'code': '610020',
            'name': 'Expense Account 2'
        })

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2022-01-20',
            'expense_line_ids': [
                Command.create({
                    # Expense on Expense Account 1
                    'name': 'expense_1',
                    'date': '2022-01-05',
                    'account_id': account_expense_1.id,
                    'product_id': self.product_c.id,
                    'total_amount': 115.0,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                    'employee_id': self.expense_employee.id,
                }),
                Command.create({
                    # Expense on Expense Account 2
                    'name': 'expense_2',
                    'date': '2022-01-08',
                    'account_id': account_expense_2.id,
                    'product_id': self.product_c.id,
                    'total_amount': 230.0,
                    'tax_ids': [Command.set(self.tax_purchase_a.ids)],
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        self.assertRecordValues(expense_sheet, [{'state': 'draft', 'total_amount': 345.0}])

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        # Check expense sheet journal entry values.
        self.assertRecordValues(expense_sheet.account_move_ids.line_ids.sorted('balance'), [
            # Receivable lines:
            {
                'balance': -345.0, # 115 + 230
                'account_id': self.company_data['default_account_payable'].id,
            },
            # Tax lines:
            {
                'balance': 15.0,
                'account_id': self.company_data['default_account_tax_purchase'].id,
            },
            {
                'balance': 30.0,
                'account_id': self.company_data['default_account_tax_purchase'].id,
            },
            # Expense line 1:
            {
                'balance': 100.0, # 115 / 1.15 (tax incl.)
                'account_id': account_expense_1.id,
            },
            # Expense line 2:
            {
                'balance': 200.0, # 230 / 1.15 (tax incl.)
                'account_id': account_expense_2.id,
            },
        ])

    def test_employee_supplier(self):
        """ Checking accounting move entries for the supplier set to the employee """

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2022-01-20',
            'expense_line_ids': [
                Command.create({
                    # Expense on Expense Account 1
                    'name': 'expense_1',
                    'date': '2022-01-05',
                    'product_id': self.product_c.id,
                    'total_amount': 115.0,
                    'employee_id': self.expense_employee.id,
                }),
                Command.create({
                    # Expense on Expense Account 2
                    'name': 'expense_2',
                    'date': '2022-01-08',
                    'product_id': self.product_c.id,
                    'total_amount': 230.0,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        # Check whether employee is set as supplier on the receipt
        self.assertRecordValues(expense_sheet.account_move_ids, [{
            'partner_id': self.expense_user_employee.partner_id.id,
        }])

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
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'employee_id': self.expense_employee.id,
                }),
                (0, 0, {
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 1.0,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        #actions
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
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
            'due_date': payment.date.strftime("%m/%d/%Y"),
            'number': ' - '.join([move.name, move.ref] if move.ref else [move.name]),
            'amount_total': formatLang(self.env, move.amount_total, currency_obj=self.env.company.currency_id),
            'amount_residual': '-',
            'amount_paid': formatLang(self.env, payment.amount_total, currency_obj=self.env.company.currency_id),
            'currency': self.env.company.currency_id
        })

    def test_hr_expense_split(self):
        """
        Check Split Expense flow.
        """
        expense = self.env['hr.expense'].create({
            'name': 'Expense To Test Split - Diego, libre dans sa tête',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_zero_cost.id,
            'total_amount': 100.00,
            'tax_ids': [(6, 0, [self.tax_purchase_a.id])],
            'analytic_distribution': {self.analytic_account_1.id: 100},
        })

        split_wizard = expense.action_split_wizard()
        wizard = self.env['hr.expense.split.wizard'].browse(split_wizard['res_id'])

        # Check default hr.expense.split values
        self.assertRecordValues(wizard.expense_split_line_ids, [
            {
                'name': expense.name,
                'wizard_id': wizard.id,
                'expense_id': expense.id,
                'product_id': expense.product_id.id,
                'tax_ids': expense.tax_ids.ids,
                'total_amount': expense.total_amount / 2,
                'amount_tax': 6.52,
                'employee_id': expense.employee_id.id,
                'company_id': expense.company_id.id,
                'currency_id': expense.currency_id.id,
                'analytic_distribution': expense.analytic_distribution,
            } for i in range(0, 2)])

        self.assertEqual(wizard.split_possible, True)
        self.assertEqual(wizard.total_amount, expense.total_amount)

        # Grant Analytic Accounting rights, to be able to modify analytic_distribution from the wizard
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        with Form(wizard) as form:
            form.expense_split_line_ids.remove(index=0)
            self.assertEqual(form.split_possible, False)

            # Check removing tax_ids and analytic_distribution
            with form.expense_split_line_ids.edit(0) as line:
                line.total_amount = 20
                line.tax_ids.clear()
                line.analytic_distribution = {}
                self.assertEqual(line.total_amount, 20)
                self.assertEqual(line.amount_tax, 0)

            self.assertEqual(form.split_possible, False)

            # This line should have the same tax_ids and analytic_distribution as original expense
            with form.expense_split_line_ids.new() as line:
                line.total_amount = 30
                self.assertEqual(line.total_amount, 30)
                self.assertEqual(line.amount_tax, 3.91)
            self.assertEqual(form.split_possible, False)
            self.assertEqual(form.total_amount, 50)

            # Check adding tax_ids and setting analytic_distribution
            with form.expense_split_line_ids.new() as line:
                line.total_amount = 50
                line.tax_ids.add(self.tax_purchase_b)
                line.analytic_distribution = {self.analytic_account_2.id: 100}
                self.assertEqual(line.total_amount, 50)
                self.assertAlmostEqual(line.amount_tax, 11.54)

            # Check wizard values
            self.assertEqual(form.total_amount, 100)
            self.assertEqual(form.total_amount_original, 100)
            self.assertAlmostEqual(form.total_amount_taxes, 15.45)
            self.assertEqual(form.split_possible, True)

        wizard.action_split_expense()
        # Check that split resulted into expenses with correct values
        expenses_after_split = self.env['hr.expense'].search(
            [
                ('name', '=', expense.name)
            ]
        )
        self.assertRecordValues(expenses_after_split.sorted('total_amount'), [
            {
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'product_id': expense.product_id.id,
                'total_amount': 20.0,
                'tax_ids': [],
                'amount_tax': 0,
                'untaxed_amount': 20,
                'analytic_distribution': False,
            },
            {
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'product_id': expense.product_id.id,
                'total_amount': 30,
                'tax_ids': [self.tax_purchase_a.id],
                'amount_tax': 3.91,
                'untaxed_amount': 26.09,
                'analytic_distribution': {str(self.analytic_account_1.id): 100},
            },
            {
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'product_id': expense.product_id.id,
                'total_amount': 50,
                'tax_ids': [self.tax_purchase_a.id, self.tax_purchase_b.id],
                'amount_tax': 11.54,
                'untaxed_amount': 38.46,
                'analytic_distribution': {str(self.analytic_account_2.id): 100},
            }
        ])

    def test_analytic_account_deleted(self):
        """ Test that an analytic account cannot be deleted if it is used in an expense """

        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for Dick Tracy',
            'employee_id': self.expense_employee.id,
        })
        expense = self.env['hr.expense'].create({
            'name': 'Choucroute Saucisse',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount': 700.00,
            'sheet_id': expense.id,
            'analytic_distribution': {
                self.analytic_account_1.id: 50,
                self.analytic_account_2.id: 50,
            },
        })

        with self.assertRaises(UserError):
            (self.analytic_account_1 | self.analytic_account_2).unlink()

        expense.unlink()
        self.analytic_account_1.unlink()

    def test_expense_sheet_due_date(self):
        """ Test expense sheet bill due date """

        self.expense_employee.user_partner_id.property_supplier_payment_term_id = self.env.ref('account.account_payment_term_30days')
        with freeze_time('2021-01-01'):
            expense_sheet = self.env['hr.expense.sheet'].create({
                'name': 'Expense for John Smith',
                'employee_id': self.expense_employee.id,
                'expense_line_ids': [Command.create({
                    'name': 'Car Travel Expenses',
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'total_amount': 350.00,
                    'date': '2021-01-01',
                })],
            })
            expense_sheet.action_submit_sheet()
            expense_sheet.action_approve_expense_sheets()
            expense_sheet.action_sheet_move_create()
            moves = expense_sheet.account_move_ids
            expected_date = fields.Date.from_string('2021-01-31')
            self.assertEqual(moves.mapped('invoice_date_due'), [expected_date], 'Bill due date should follow employee payment terms')

    def test_inverse_total_amount(self):
        """ Test if the inverse method works correctly """

        expense = self.env['hr.expense'].create({
            'name': 'Choucroute Saucisse',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount': 60,
            'tax_ids': [self.tax_purchase_a.id, self.tax_purchase_b.id],
            'analytic_distribution': {
                self.analytic_account_1.id: 50,
                self.analytic_account_2.id: 50,
            },
        })

        expense.total_amount = 90

        self.assertEqual(expense.unit_amount, 90, 'Unit amount should be the same as total amount was written to')

    def test_expense_from_attachments(self):
        # avoid passing through extraction when installed
        if 'hr.expense.extract.words' in self.env:
            self.env.company.expense_extract_show_ocr_option_selection = 'no_send'
        self.env.user.employee_id = self.expense_employee.id
        attachment = self.env['ir.attachment'].create({
            'datas': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file.png',
            'res_model': 'hr.expense',
        })
        product = self.env['product.product'].search([('can_be_expensed', '=', True)])
        # reproduce the same way we get the product by default
        if product:
            product = product.filtered(lambda p: p.default_code == "EXP_GEN") or product[0]
        product.property_account_expense_id = self.company_data['default_account_payable']

        self.env['hr.expense'].create_expense_from_attachments(attachment.id)
        expense = self.env['hr.expense'].search([], order='id desc', limit=1)
        self.assertEqual(expense.account_id, product.property_account_expense_id, "The expense account should be the default one of the product")

    def test_expense_sheet_payment_states(self):
        sheet_company = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'payment_mode': 'company_account',
                    'employee_id': self.expense_employee.id
                }),
                Command.create({
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'payment_mode': 'company_account',
                    'employee_id': self.expense_employee.id
                }),
            ],
        })
        sheet_own = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet 2',
            'payment_mode': 'own_account',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_3',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 4.0,
                    'payment_mode': 'own_account',
                    'employee_id': self.expense_employee.id
                }),
                Command.create({
                    'name': 'expense_4',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 8.0,
                    'payment_mode': 'own_account',
                    'employee_id': self.expense_employee.id
                }),
            ],
        })
        sheets = self.env['hr.expense.sheet'].browse((sheet_company.id, sheet_own.id))
        #actions
        self.assertEqual('draft', sheet_own.state)
        self.assertEqual('not_paid', sheet_own.payment_state)
        self.assertEqual('draft', sheet_company.state)
        self.assertEqual('not_paid', sheet_company.payment_state)

        sheets.action_submit_sheet()
        self.assertEqual('submit', sheet_own.state)
        self.assertEqual('not_paid', sheet_own.payment_state)
        self.assertEqual('submit', sheet_company.state)
        self.assertEqual('not_paid', sheet_company.payment_state)

        sheets.action_approve_expense_sheets()
        self.assertEqual('approve', sheet_own.state)
        self.assertEqual('not_paid', sheet_own.payment_state)
        self.assertEqual('approve', sheet_company.state)
        self.assertEqual('not_paid', sheet_company.payment_state)

        sheets.action_sheet_move_create()
        self.assertEqual('post', sheet_own.state)
        self.assertEqual('not_paid', sheet_own.payment_state)
        self.assertEqual('done', sheet_company.state)
        self.assertEqual('paid', sheet_company.payment_state)

        own_payment = sheet_own.account_move_ids[0].action_register_payment()
        own_wizard = Form(self.env['account.payment.register'].with_context(own_payment['context'])).save()
        own_wizard.action_create_payments()
        self.assertEqual('done', sheet_own.state)
        self.assertIn(sheet_own.payment_state, {'in_payment', 'paid'})

    def test_expense_sheet_payments_amount(self):
        sheet_company = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'payment_mode': 'company_account',
                    'employee_id': self.expense_employee.id
                }),
                Command.create({
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'payment_mode': 'company_account',
                    'employee_id': self.expense_employee.id
                }),
            ],
        })
        sheet_own = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet 2',
            'payment_mode': 'own_account',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_3',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 4.0,
                    'payment_mode': 'own_account',
                    'employee_id': self.expense_employee.id
                }),
                Command.create({
                    'name': 'expense_4',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 8.0,
                    'payment_mode': 'own_account',
                    'employee_id': self.expense_employee.id
                }),
            ],
        })
        sheets = self.env['hr.expense.sheet'].browse((sheet_company.id, sheet_own.id))
        sheets.action_submit_sheet()
        sheets.action_approve_expense_sheets()
        sheets.action_sheet_move_create()

        self.assertEqual(1, len(sheet_own.account_move_ids), "When an expense is paid by the employee, one move is created")
        self.assertEqual(2, len(sheet_company.account_move_ids), "When an expense is paid by the company, one move is created per expense")

    def test_payment_unlinks(self):
        sheet_company = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'payment_mode': 'company_account',
                    'employee_id': self.expense_employee.id
                }),
                Command.create({
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'payment_mode': 'company_account',
                    'employee_id': self.expense_employee.id
                }),
            ],
        })
        sheet_own = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet 2',
            'payment_mode': 'own_account',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_3',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 4.0,
                    'payment_mode': 'own_account',
                    'employee_id': self.expense_employee.id
                }),
                Command.create({
                    'name': 'expense_4',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 8.0,
                    'payment_mode': 'own_account',
                    'employee_id': self.expense_employee.id
                }),
            ],
        })
        sheets = sheet_company | sheet_own
        sheets.action_submit_sheet()
        sheets.action_approve_expense_sheets()
        sheets.action_sheet_move_create()
        own_payment = sheet_own.account_move_ids[0].action_register_payment()
        own_wizard = Form(self.env['account.payment.register'].with_context(own_payment['context'])).save()
        own_wizard.action_create_payments()
        sheet_own.account_move_ids.button_draft()
        sheet_own.account_move_ids.unlink()

        with self.assertRaises(UserError, msg="For company-paid expenses report, deleting payments is an all-or-nothing situation"):
            sheet_company.account_move_ids[:-1].payment_id.unlink()

        sheet_company.account_move_ids.payment_id.unlink()
        self.assertRecordValues(sheets.sorted('payment_mode'), [
            {'payment_mode': 'company_account', 'state': 'approve', 'payment_state': 'not_paid', 'account_move_ids': self.env['account.move']},
            {'payment_mode': 'own_account', 'state': 'approve', 'payment_state': 'not_paid', 'account_move_ids': self.env['account.move']},
        ])

    def test_multiple_payments(self):
        # pylint: disable=bad-whitespace
        foreign_currency = self.env['res.currency'].create({
            'name': 'Exposure',
            'symbol': ' ',
            'rounding': 0.01,
            'position': 'after',
            'currency_unit_label': 'Nothing',
            'currency_subunit_label': 'Smaller Nothing',
        })
        self.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 1/1.52890,
            'currency_id': foreign_currency.id,
            'company_id': self.company_data['company'].id,
        })
        tax = self.env['account.tax'].create({
            'name': 'Tax Expense 15%',
            'amount': 15,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'price_include': True,
        })

        expense_sheet_own_account = self.env['hr.expense.sheet'].create({
            'name': "Own Expenses",
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01',
            'expense_line_ids': [
                Command.create({
                    'name': 'Own expense',
                    'date': '2022-11-16',
                    'payment_mode': 'own_account',
                    'total_amount': 1000.00,
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'currency_id': self.company_data['currency'].id,
                    'tax_ids': [Command.set(tax.ids)],
                }),
                Command.create({
                    'name': 'Own expense 2',
                    'date': '2022-11-17',
                    'payment_mode': 'own_account',
                    'total_amount': 1000.00,
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'currency_id': foreign_currency.id,  # rate is 1:1.5289
                    'tax_ids': [Command.set(tax.ids)],
            })
            ],
        })
        expense_sheet_company_account = self.env['hr.expense.sheet'].create({
            'name': "Company Expenses",
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01',
            'expense_line_ids': [
                Command.create({
                    'name': 'Company expense',
                    'date': '2022-11-16',
                    'payment_mode': 'company_account',
                    'total_amount': 1000.00,
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'currency_id': self.company_data['currency'].id,
                    'tax_ids': [Command.set(tax.ids)],
                }),
                Command.create({
                    'name': 'Company expense 2',
                    'date': '2022-11-17',
                    'payment_mode': 'company_account',
                    'total_amount': 1000.00,
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'currency_id': foreign_currency.id,  # rate is 1:1.5289
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })

        sheets = expense_sheet_own_account + expense_sheet_company_account
        self.assertRecordValues(sheets.expense_line_ids, [
            {'total_amount': 1000.00, 'total_amount_company': 1000.00, 'amount_tax': 130.43, 'amount_tax_company': 130.43},
            {'total_amount': 1000.00, 'total_amount_company': 1528.90, 'amount_tax': 130.43, 'amount_tax_company': 199.42},
            {'total_amount': 1000.00, 'total_amount_company': 1000.00, 'amount_tax': 130.43, 'amount_tax_company': 130.43},
            {'total_amount': 1000.00, 'total_amount_company': 1528.90, 'amount_tax': 130.43, 'amount_tax_company': 199.42},
        ])

        sheets.action_submit_sheet()
        sheets.action_approve_expense_sheets()
        sheets.action_sheet_move_create()
        self.assertRecordValues(expense_sheet_own_account.account_move_ids, [{'ref': 'Own Expenses'}])  # One move with the report name in ref
        self.assertRecordValues(expense_sheet_company_account.account_move_ids.sorted('ref'), [
            {'ref': 'Company expense'},
            {'ref': 'Company expense 2'},
        ])  # Two moves with the expense names in ref
        self.assertRecordValues(expense_sheet_own_account.account_move_ids.line_ids, [
            {'balance':  1329.48, 'amount_currency':  1329.48, 'currency_id': self.company_data['currency'].id},
            {'balance':   869.57, 'amount_currency':   869.57, 'currency_id': self.company_data['currency'].id},
            {'balance':   199.42, 'amount_currency':   199.42, 'currency_id': self.company_data['currency'].id},
            {'balance':   130.43, 'amount_currency':   130.43, 'currency_id': self.company_data['currency'].id},
            {'balance': -2528.90, 'amount_currency': -2528.90, 'currency_id': self.company_data['currency'].id},
        ])

        self.assertRecordValues(expense_sheet_company_account.account_move_ids.sorted('ref').line_ids, [
            # First move
            {'balance':   869.57, 'amount_currency':   869.57, 'currency_id': self.company_data['currency'].id},
            {'balance':   130.43, 'amount_currency':   130.43, 'currency_id': self.company_data['currency'].id},
            {'balance': -1000.00, 'amount_currency': -1000.00, 'currency_id': self.company_data['currency'].id},
            # Second move
            {'balance':  1329.49, 'amount_currency':   869.57, 'currency_id': foreign_currency.id},  # Values are different due conversion issues
            {'balance':   199.41, 'amount_currency':   130.43, 'currency_id': foreign_currency.id},
            {'balance': -1528.90, 'amount_currency': -1000.00, 'currency_id': foreign_currency.id},
        ])

    def test_currency_rate_override(self):
        """ Checks that the currency rate is recomputed properly when the total in company currency is set to a new value """
        foreign_currency = self.env['res.currency'].create({
            'name': 'Exposure',
            'symbol': ' ',
            'rounding': 0.01,
            'position': 'after',
            'currency_unit_label': 'Nothing',
            'currency_subunit_label': 'Smaller Nothing',
        })
        self.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 1/1.52,
            'currency_id': foreign_currency.id,
            'company_id': self.company_data['company'].id,
        })
        expense = self.env['hr.expense'].create({
            'name': 'Company expense',
            'date': '2022-11-16',
            'payment_mode': 'company_account',
            'total_amount': 1000.00,
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'currency_id': self.currency_data['currency'].id,  # rate is 1:2
        })
        expense_2 = self.env['hr.expense'].create({
            'name': 'Company expense',
            'date': '2022-11-16',
            'payment_mode': 'company_account',
            'total_amount': 1000.00,
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'currency_id': foreign_currency.id,  # rate is 1.52
        })
        expense_3 = self.env['hr.expense'].create({
            'name': 'Company expense',
            'date': '2022-11-16',
            'payment_mode': 'company_account',
            'total_amount': 1000.00,
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'currency_id': foreign_currency.id,  # rate is 1.52
        })
        expenses = expense | expense_2 | expense_3
        self.assertRecordValues(expenses, [
            {'currency_rate': 0.50, 'total_amount': 1000.00, 'total_amount_company':  500.00, 'currency_id': self.currency_data['currency'].id},
            {'currency_rate': 1.52, 'total_amount': 1000.00, 'total_amount_company': 1520.00, 'currency_id': foreign_currency.id},
            {'currency_rate': 1.52, 'total_amount': 1000.00, 'total_amount_company': 1520.00, 'currency_id': foreign_currency.id},
        ])

        # Changing rate on the two first expenses
        expense.write({'total_amount_company': 1000.00})
        expense_2.write({'total_amount_company': 2000.00})
        self.assertRecordValues(expenses, [
            {'currency_rate': 1.00, 'total_amount': 1000.00, 'total_amount_company': 1000.00},  # Rate should change
            {'currency_rate': 2.00, 'total_amount': 1000.00, 'total_amount_company': 2000.00},  # Rate should change
            {'currency_rate': 1.52, 'total_amount': 1000.00, 'total_amount_company': 1520.00},  # Rate should NOT change
        ])

        # Sheet and move creation should not touch the rates anymore
        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for Company',
            'employee_id': self.expense_employee.id,
            'expense_line_ids': expenses,
        })
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()
        self.assertRecordValues(expense_sheet.account_move_ids, [
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1000.00, 'currency_id': self.currency_data['currency'].id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 2000.00, 'currency_id': foreign_currency.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1520.00, 'currency_id': foreign_currency.id},
        ])

    def test_attachments_in_move_from_own_expense(self):
        """ Checks that journal entries created form expense reports paid by employee have a copy of the attachments in the expense. """
        expense = self.env['hr.expense'].create({
            'name': 'Employee expense',
            'date': '2022-11-16',
            'payment_mode': 'own_account',
            'total_amount': 1000.00,
            'employee_id': self.expense_employee.id,
        })
        expense_2 = self.env['hr.expense'].create({
            'name': 'Employee expense 2',
            'date': '2022-11-16',
            'payment_mode': 'own_account',
            'total_amount': 1000.00,
            'employee_id': self.expense_employee.id,
        })
        attachment = self.env['ir.attachment'].create({
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file1.png',
            'res_model': 'hr.expense',
            'res_id': expense.id,
        })
        attachment_2 = self.env['ir.attachment'].create({
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file2.png',
            'res_model': 'hr.expense',
            'res_id': expense_2.id,
        })

        expense.message_main_attachment_id = attachment
        expense_2.message_main_attachment_id = attachment_2
        expenses = expense | expense_2

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expenses paid by employee',
            'employee_id': self.expense_employee.id,
            'expense_line_ids': expenses,
        })
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        self.assertRecordValues(expense_sheet.account_move_ids.attachment_ids, [
            {
                'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
                'name': 'file1.png',
                'res_model': 'account.move',
                'res_id': expense_sheet.account_move_ids.id
            },
            {
                'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
                'name': 'file2.png',
                'res_model': 'account.move',
                'res_id': expense_sheet.account_move_ids.id
            }
        ])

    def test_attachments_in_move_from_company_expense(self):
        """ Checks that journal entries created form expense reports paid by company have a copy of the attachments in the expense. """
        expense = self.env['hr.expense'].create({
            'name': 'Company expense',
            'date': '2022-11-16',
            'payment_mode': 'company_account',
            'total_amount': 1000.00,
            'employee_id': self.expense_employee.id,
        })
        expense_2 = self.env['hr.expense'].create({
            'name': 'Company expense 2',
            'date': '2022-11-16',
            'payment_mode': 'company_account',
            'total_amount': 1000.00,
            'employee_id': self.expense_employee.id,
        })
        attachment = self.env['ir.attachment'].create({
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file1.png',
            'res_model': 'hr.expense',
            'res_id': expense.id,
        })
        attachment_2 = self.env['ir.attachment'].create({
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file2.png',
            'res_model': 'hr.expense',
            'res_id': expense_2.id,
        })

        expense.message_main_attachment_id = attachment
        expense_2.message_main_attachment_id = attachment_2
        expenses = expense | expense_2

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expenses paid by company',
            'employee_id': self.expense_employee.id,
            'expense_line_ids': expenses,
        })
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        self.assertRecordValues(expense_sheet.account_move_ids[0].attachment_ids, [{
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file1.png',
            'res_model': 'account.move',
            'res_id': expense_sheet.account_move_ids[0].id
        }])

        self.assertRecordValues(expense_sheet.account_move_ids[1].attachment_ids, [{
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file2.png',
            'res_model': 'account.move',
            'res_id': expense_sheet.account_move_ids[1].id
        }])
