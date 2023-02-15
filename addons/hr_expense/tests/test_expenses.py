# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
            'product_id': self.product_a.id,
            'unit_amount': 350.00,
        })

        expense2 = self.env['hr.expense'].create({
            'name': 'Team building at Huy',
            'employee_id': employee.id,
            'product_id': self.product_a.id,
            'unit_amount': 2500.00,
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

        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ref': 'pay_ref',
            'amount': -350.0,
            'partner_id': self.expense_employee.address_home_id.id,
        })

        # Reconcile without the bank reconciliation widget since the widget is in enterprise.
        _st_liquidity_lines, st_suspense_lines, _st_other_lines = statement_line\
            .with_context(skip_account_move_synchronization=True)\
            ._seek_for_lines()
        st_suspense_lines.account_id = liquidity_lines1.account_id
        (st_suspense_lines + liquidity_lines1 + liquidity_lines2).reconcile()

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
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                }),
                (0, 0, {
                    # Expense with foreign currency (rate 1:3).
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_b.id,
                    'unit_amount': 1500.0,
                    'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)],
                    'analytic_distribution': {self.analytic_account_2.id: 100},
                    'currency_id': self.currency_data['currency'].id,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

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
                'analytic_distribution': False,
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
                'analytic_distribution': False,
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
                'debit': 652.17,
                'credit': 0.0,
                'amount_currency': 1304.348, # untaxed amount
                'account_id': self.product_b.property_account_expense_id.id,
                'product_id': self.product_b.id,
                'currency_id': self.currency_data['currency'].id,
                'tax_line_id': False,
                'analytic_distribution': {str(self.analytic_account_2.id): 100},
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
                'analytic_distribution': {str(self.analytic_account_1.id): 100},
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
            expense_sheet = expense_sheet_form.save()

        expense_sheet.action_submit_sheet()
        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

    def test_account_entry_multi_currency(self):
        """ Checking accounting move entries and analytic entries when submitting expense. With
            multi-currency. And taxes. """
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
            'analytic_distribution': {self.analytic_account_1.id: 100},
            'currency_id': self.currency_data['currency'].id,
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
        # Should get this result [(0.0, 350.0, -700.0), (318.18, 0.0, 636.36), (31.82, 0.0, 63.64)]
        analytic_line = expense.account_move_id.line_ids.analytic_line_ids
        self.assertEqual(len(analytic_line), 1)
        self.assertInvoiceValues(expense.account_move_id, [
            {
                'balance': 318.18,
                'amount_currency': 636.364,
                'product_id': self.product_a.id,
                'price_unit': 700.0,
                'price_subtotal': 636.364,
                'price_total': 700.0,
                'analytic_line_ids': analytic_line.ids,
            }, {
                'balance': 31.82,
                'amount_currency': 63.636,
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'analytic_line_ids': [],
            }, {
                'balance': -350.0,
                'amount_currency': -700.0,
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'analytic_line_ids': [],
            },
        ], {
            'amount_total': 700.0,
        })

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
                'analytic_distribution': {str(self.analytic_account_1.id): 100},
            })

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
        wizard.group_payment = False
        action = wizard.action_create_payments()
        self.assertEqual(sheet.state, 'done', 'all account.move.line linked to expenses must be reconciled after payment')
        move = self.env['account.payment'].search(action['domain']).move_id
        move.button_cancel()
        self.assertEqual(sheet.state, 'done', 'Sheet state must not change when the payment linked to that sheet is canceled')

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
                    'product_id': self.product_a.id,
                    'unit_amount': 115.0,
                    'employee_id': self.expense_employee.id,
                }),
                Command.create({
                    # Expense on Expense Account 2
                    'name': 'expense_2',
                    'date': '2022-01-08',
                    'account_id': account_expense_2.id,
                    'product_id': self.product_a.id,
                    'unit_amount': 230.0,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        self.assertRecordValues(expense_sheet, [{'state': 'draft', 'total_amount': 345.0}])

        expense_sheet.action_submit_sheet()
        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        # Check expense sheet journal entry values.
        self.assertRecordValues(expense_sheet.account_move_id.line_ids.sorted('balance'), [
            # Receivable lines:
            {
                'balance': -230.0,
                'account_id': self.company_data['default_account_payable'].id,
            },
            {
                'balance': -115.0,
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
                'balance': 100.0,
                'account_id': account_expense_1.id,
            },
            # Expense line 2:
            {
                'balance': 200.0,
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
                    'product_id': self.product_a.id,
                    'unit_amount': 115.0,
                    'employee_id': self.expense_employee.id,
                }),
                Command.create({
                    # Expense on Expense Account 2
                    'name': 'expense_2',
                    'date': '2022-01-08',
                    'product_id': self.product_a.id,
                    'unit_amount': 230.0,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        # Check whether employee is set as supplier on the receipt
        self.assertRecordValues(expense_sheet.account_move_id, [{
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
            wiz_form.group_payment = False
        wizard = wiz_form.save()
        action = wizard.action_create_payments()
        self.assertEqual(sheet.state, 'done', 'all account.move.line linked to expenses must be reconciled after payment')

        payments = self.env[action['res_model']].search(action['domain'])
        for payment in payments:
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
            'product_id': self.product_a.id,
            'unit_amount': 700.00,
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
