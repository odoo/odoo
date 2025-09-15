# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged, Form


@tagged('-at_install', 'post_install')
class TestExpenses(TestExpenseCommon):
    #############################################
    #  Test Expense flows
    #############################################
    def test_expense_main_flow(self):
        """
        Test the main flows of expense
        This includes:
            - Approval flows for expense paid by company and employee up to reconciliation
            - price_unit, total_amount_currency and quantity computation
            - Split payments into one payment per expense when paid by company
            - Override account on expense
            - Payment states and payment terms
            - Unlinking payments reverts to approved state
            - Cannot delete an analytic account if linked to an expense
        """

        self.expense_employee.user_partner_id.property_supplier_payment_term_id = self.env.ref('account.account_payment_term_30days')
        expenses_by_employee = self.create_expenses([
            {
                'name': 'Employee PA 2*800 + 15%',  # Taxes are included
                'employee_id': self.expense_employee.id,
                'account_id': self.expense_account.id,  # Test with a specific account override
                'product_id': self.product_a.id,
                'quantity': 2,
                'payment_mode': 'own_account',
                'company_id': self.company_data['company'].id,
                'date': '2021-10-14',
                'analytic_distribution': {self.analytic_account_1.id: 100},
            }, {
                'name': 'Employee PB 160 + 2*15%',  # Taxes are included
                'employee_id': self.expense_employee.id,
                'product_id': self.product_b.id,
                'payment_mode': 'own_account',
                'company_id': self.company_data['company'].id,
                'date': '2021-10-13',
                'analytic_distribution': {self.analytic_account_2.id: 100},
            },
        ])
        expenses_by_company = self.create_expenses([
            {
                'name': 'Company PC 1000 + 15%',  # Taxes are included
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': '2021-10-12',
                'payment_mode': 'company_account',
                'company_id': self.company_data['company'].id,
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            }, {
                'name': 'Company PB 160 + 2*15%',  # Taxes are included
                'employee_id': self.expense_employee.id,
                'product_id': self.product_b.id,
                'payment_mode': 'company_account',
                'company_id': self.company_data['company'].id,
                'date': '2021-10-11',
            },
        ])
        all_expenses = expenses_by_employee | expenses_by_company

        # Checking expense values at creation
        self.assertRecordValues(all_expenses, [
            {'name': 'Employee PA 2*800 + 15%', 'total_amount_currency': 1600.00, 'untaxed_amount_currency': 1391.30, 'price_unit':  800.00, 'tax_amount_currency': 208.70, 'state': 'draft'},
            {'name': 'Employee PB 160 + 2*15%', 'total_amount_currency':  160.00, 'untaxed_amount_currency':  123.08, 'price_unit':  160.00, 'tax_amount_currency':  36.92, 'state': 'draft'},
            {'name': 'Company PC 1000 + 15%',   'total_amount_currency': 1000.00, 'untaxed_amount_currency':  869.57, 'price_unit': 1000.00, 'tax_amount_currency': 130.43, 'state': 'draft'},
            {'name': 'Company PB 160 + 2*15%',  'total_amount_currency':  160.00, 'untaxed_amount_currency':  123.08, 'price_unit':  160.00, 'tax_amount_currency':  36.92, 'state': 'draft'},
        ])

        # Submitting properly change states
        all_expenses.action_submit()
        self.assertRecordValues(all_expenses, [
            {'state': 'submitted'},
            {'state': 'submitted'},
            {'state': 'submitted'},
            {'state': 'submitted'},
        ])

        # Approving properly change states & create moves & payments
        all_expenses.action_approve()
        self.assertRecordValues(all_expenses, [
            {'state': 'approved', 'account_move_id': False},
            {'state': 'approved', 'account_move_id': False},
            {'state': 'approved', 'account_move_id': False},
            {'state': 'approved', 'account_move_id': False},
        ])
        # Post a payment for 'company_account' (and its move(s)) and a receipt  for 'own_account'
        expenses_by_company.action_post()
        self.post_expenses_with_wizard(expenses_by_employee[0], date=date(2021, 10, 10))
        self.post_expenses_with_wizard(expenses_by_employee[1], date=date(2021, 10, 31))
        self.assertRecordValues(all_expenses, [
            # As the payment is not done yet those are still in "posted"
            {'payment_mode': 'own_account',     'state': 'posted'},
            {'payment_mode': 'own_account',     'state': 'posted'},
            # Expenses paid by company don't use accounting date since they are already paid and posted directly
            {'payment_mode': 'company_account', 'state': 'paid'},
            {'payment_mode': 'company_account', 'state': 'paid'},
        ])

        employee_partner_id = self.expense_user_employee.partner_id.id
        self.assertRecordValues(expenses_by_employee.account_move_id, [
            {'amount_total': 1600.00, 'ref': 'Employee PA 2*800 + 15%', 'state': 'posted', 'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 10), 'partner_id': employee_partner_id},
            {'amount_total':  160.00, 'ref': 'Employee PB 160 + 2*15%', 'state': 'posted', 'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 31), 'partner_id': employee_partner_id},
        ])

        self.assertRecordValues(expenses_by_company.account_move_id, [
            {'amount_total':  1000.00, 'ref': 'Company PC 1000 + 15%',  'state': 'posted', 'date': date(2021, 10, 12), 'invoice_date': False, 'partner_id': False},
            {'amount_total':   160.00, 'ref': 'Company PB 160 + 2*15%', 'state': 'posted', 'date': date(2021, 10, 11), 'invoice_date': False, 'partner_id': False},
        ])

        tax_account_id = self.company_data['default_account_tax_purchase'].id
        default_account_payable_id = self.company_data['default_account_payable'].id
        product_b_account_id = self.product_b.property_account_expense_id.id
        product_c_account_id = self.product_c.property_account_expense_id.id
        company_payment_account_id = self.outbound_payment_method_line.payment_account_id.id
        # One payment per expense
        self.assertRecordValues(all_expenses.account_move_id.line_ids.sorted(lambda line: (line.move_id, line)), [
            # own_account expense 1 move
            {'balance':  1391.30, 'account_id': self.expense_account.id,    'name': 'expense_employee: Employee PA 2*800 + 15%', 'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 10)},
            {'balance':   208.70, 'account_id': tax_account_id,             'name': '15%',                                       'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 10)},
            {'balance': -1600.00, 'account_id': default_account_payable_id, 'name': False,                                       'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 10)},

            # own_account expense 2 move
            {'balance':   123.08, 'account_id': product_b_account_id,       'name': 'expense_employee: Employee PB 160 + 2*15%', 'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 31)},
            {'balance':    18.46, 'account_id': tax_account_id,             'name': '15%',                                       'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 31)},
            {'balance':    18.46, 'account_id': tax_account_id,             'name': '15% (copy)',                                'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 31)},
            {'balance':  -160.00, 'account_id': default_account_payable_id, 'name': False,                                       'date': date(2021, 10, 31), 'invoice_date': date(2021, 10, 31)},

            # company_account expense 1 move
            {'balance':   869.57, 'account_id': product_c_account_id,       'name': 'expense_employee: Company PC 1000 + 15%',   'date': date(2021, 10, 12), 'invoice_date': False},
            {'balance':   130.43, 'account_id': tax_account_id,             'name': '15%',                                       'date': date(2021, 10, 12), 'invoice_date': False},
            {'balance': -1000.00, 'account_id': company_payment_account_id, 'name': 'expense_employee: Company PC 1000 + 15%',   'date': date(2021, 10, 12), 'invoice_date': False},

            # company_account expense 2 move
            {'balance':  123.08, 'account_id': product_b_account_id,        'name': 'expense_employee: Company PB 160 + 2*15%',  'date': date(2021, 10, 11), 'invoice_date': False},
            {'balance':   18.46, 'account_id': tax_account_id,              'name': '15%',                                       'date': date(2021, 10, 11), 'invoice_date': False},
            {'balance':   18.46, 'account_id': tax_account_id,              'name': '15% (copy)',                                'date': date(2021, 10, 11), 'invoice_date': False},
            {'balance': -160.00, 'account_id': company_payment_account_id,  'name': 'expense_employee: Company PB 160 + 2*15%',  'date': date(2021, 10, 11), 'invoice_date': False},

        ])

        in_payment_state = expenses_by_employee.account_move_id._get_invoice_in_payment_state()
        first_expense_by_employee = expenses_by_employee[0]
        first_expense_by_company = expenses_by_company[0]

        # Own_account partial payment
        payment_1 = self.get_new_payment(first_expense_by_employee, 1000.0)
        liquidity_lines1 = payment_1._seek_for_lines()[0]
        self.assertEqual(first_expense_by_employee.state, in_payment_state)

        # own_account remaining payment
        payment_2 = self.get_new_payment(first_expense_by_employee, 600.0)
        liquidity_lines2 = payment_2._seek_for_lines()[0]
        self.assertEqual(first_expense_by_employee.state, in_payment_state)

        # Reconciling own_account
        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ref': 'pay_ref',
            'amount': -1600.0,
            'partner_id': self.expense_employee.work_contact_id.id,
        })

        # Reconcile without the bank reconciliation widget since the widget is in enterprise.
        _trash, st_suspense_lines, _trash = statement_line.with_context(skip_account_move_synchronization=True)._seek_for_lines()
        st_suspense_lines.account_id = liquidity_lines1.account_id
        (st_suspense_lines + liquidity_lines1 + liquidity_lines2).reconcile()
        self.assertEqual(first_expense_by_employee.state, 'paid')

        # Trying to delete analytic accounts should be forbidden if linked to an expense
        with self.assertRaises(UserError):
            (self.analytic_account_1 | self.analytic_account_2).unlink()

        # Unlinking moves
        (payment_1 | payment_2).action_draft()
        (payment_1 | payment_2).move_id.line_ids.remove_move_reconcile()
        self.assertEqual(first_expense_by_employee.state, 'posted')
        expenses_by_employee.account_move_id.button_draft()
        expenses_by_employee.account_move_id.unlink()
        self.assertFalse(expenses_by_employee.account_move_id)

        first_expense_by_company.account_move_id.origin_payment_id.unlink()
        self.assertFalse(first_expense_by_company.account_move_id)

        self.assertRecordValues(first_expense_by_employee | first_expense_by_company, [
            {'payment_mode': 'own_account',     'state': 'approved'},
            {'payment_mode': 'company_account', 'state': 'approved'},
        ])

        first_expense_by_employee.action_reset()
        self.assertEqual(first_expense_by_employee.state, 'draft')
        first_expense_by_employee.unlink()
        # Only possible if no expense linked to the account
        self.analytic_account_1.unlink()

    def test_expense_split_flow(self):
        """ Check Split Expense flow. """
        # Grant Analytic Accounting rights, to be able to modify analytic_distribution from the wizard
        self.env.user.group_ids += self.env.ref('analytic.group_analytic_accounting')

        expense = self.create_expenses({
            'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            'analytic_distribution': {self.analytic_account_1.id: 100}
        })

        wizard = self.env['hr.expense.split.wizard'].browse(expense.action_split_wizard()['res_id'])

        # Check default hr.expense.split values
        self.assertRecordValues(wizard.expense_split_line_ids, [
            {
                'name': expense.name,
                'wizard_id': wizard.id,
                'expense_id': expense.id,
                'product_id': expense.product_id.id,
                'tax_ids': expense.tax_ids.ids,
                'total_amount_currency': expense.total_amount_currency / 2,
                'tax_amount_currency': 65.22,
                'employee_id': expense.employee_id.id,
                'company_id': expense.company_id.id,
                'currency_id': expense.currency_id.id,
                'analytic_distribution': expense.analytic_distribution,
            }] * 2)
        self.assertRecordValues(wizard, [{'split_possible': True, 'total_amount_currency': expense.total_amount_currency}])

        with Form(wizard) as form:
            form.expense_split_line_ids.remove(index=0)
            self.assertEqual(form.split_possible, False)

            # Check removing tax_ids and analytic_distribution
            with form.expense_split_line_ids.edit(0) as line:
                line.total_amount_currency = 200.00
                line.tax_ids.clear()
                line.analytic_distribution = {}
                self.assertEqual(line.total_amount_currency, 200.00)
                self.assertEqual(line.tax_amount_currency, 0.00)
            self.assertEqual(form.split_possible, False)

            # This line should have the same tax_ids and analytic_distribution as original expense
            with form.expense_split_line_ids.new() as line:
                line.total_amount_currency = 300.00
                self.assertEqual(line.total_amount_currency, 300.00)
                self.assertEqual(line.tax_amount_currency, 39.13)
                self.assertDictEqual(line.analytic_distribution, expense.analytic_distribution)
            self.assertEqual(form.split_possible, False)
            self.assertEqual(form.total_amount_currency, 500.00)

            # Check adding tax_ids and setting analytic_distribution
            with form.expense_split_line_ids.new() as line:
                line.total_amount_currency = 500.00
                line.tax_ids.add(self.tax_purchase_b)
                line.analytic_distribution = {self.analytic_account_2.id: 100}
                self.assertEqual(line.total_amount_currency, 500.00)
                self.assertEqual(line.tax_amount_currency, 115.38)

        # Check wizard values
        self.assertRecordValues(wizard, [
            {'total_amount_currency': 1000.00, 'total_amount_currency_original': 1000.00, 'tax_amount_currency': 154.51, 'split_possible': True}
        ])

        wizard.action_split_expense()
        # Check that split resulted into expenses with correct values
        expenses_after_split = self.env['hr.expense'].search([('name', '=', expense.name)])
        self.assertRecordValues(expenses_after_split.sorted('total_amount_currency'), [
            {
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'product_id': expense.product_id.id,
                'total_amount_currency': 200.00,
                'tax_ids': [],
                'tax_amount_currency': 0.00,
                'untaxed_amount_currency': 200.00,
                'analytic_distribution': False,
                'split_expense_origin_id': expense.id,
            }, {
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'product_id': expense.product_id.id,
                'total_amount_currency': 300.00,
                'tax_ids': [self.tax_purchase_a.id],
                'tax_amount_currency': 39.13,
                'untaxed_amount_currency': 260.87,
                'analytic_distribution': {str(self.analytic_account_1.id): 100},
                'split_expense_origin_id': expense.id,
            }, {
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'product_id': expense.product_id.id,
                'total_amount_currency': 500.00,
                'tax_ids': [self.tax_purchase_a.id, self.tax_purchase_b.id],
                'tax_amount_currency': 115.38,
                'untaxed_amount_currency': 384.62,
                'analytic_distribution': {str(self.analytic_account_2.id): 100},
                'split_expense_origin_id': expense.id,
            }
        ])

    #############################################
    #  Test Multi-currency
    #############################################

    def test_expense_multi_currencies(self):
        """
        Checks that the currency rate is recomputed properly when the total in company currency is set to a new value
        """
        foreign_currency_1 = self.other_currency
        foreign_currency_2 = self.setup_other_currency('GBP', rounding=0.01, rates=([('2016-01-01', 1 / 1.52)]))
        foreign_sale_journal = self.company_data['default_journal_sale'].copy()
        foreign_sale_journal.currency_id = foreign_currency_2.id

        foreign_expense_1, foreign_expense_2, foreign_expense_3 = self.create_expenses([{
                'name': 'foreign_expense_1',
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'currency_id': foreign_currency_1.id,  # rate is 1:2
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            },
            {
                'name': 'foreign_expense_2',
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'currency_id': foreign_currency_2.id,  # rate is 1:1.52
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            },
            {
                'name': 'foreign_expense_3',
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'total_amount': 3000.00,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'currency_id': foreign_currency_2.id,  # default rate is 1:1.52, should be overridden to 1:3
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            },
        ]).sorted('name')
        all_expenses = foreign_expense_1 | foreign_expense_2 | foreign_expense_3
        self.assertRecordValues(all_expenses, [
            {'total_amount':  500.00, 'total_amount_currency': 1000.00, 'currency_rate': 0.50},
            {'total_amount': 1520.00, 'total_amount_currency': 1000.00, 'currency_rate': 1.52},
            {'total_amount': 3000.00, 'total_amount_currency': 1000.00, 'currency_rate': 3.00},
        ])

        # Manually changing rate on the two first expenses after creation to check they recompute properly
        # Back-end override
        foreign_expense_1.total_amount = 1000.00
        self.assertRecordValues(foreign_expense_1, [
            {'total_amount': 1000.00, 'total_amount_currency': 1000.00, 'currency_rate': 1.0},
        ])

        # Front-end override
        with Form(foreign_expense_2) as expense_form:
            expense_form.total_amount = 2000.00
        self.assertRecordValues(foreign_expense_2, [
            {'total_amount': 2000.00, 'total_amount_currency': 1000.00, 'currency_rate': 2.0},
        ])

        # Move creation should not touch the rates anymore
        all_expenses.action_submit()
        all_expenses._do_approve()  # Skip duplicate wizard
        self.post_expenses_with_wizard(all_expenses, journal=foreign_sale_journal)
        self.assertRecordValues(all_expenses.account_move_id.sorted('id'), [
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1000.00, 'currency_id': foreign_currency_1.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 2000.00, 'currency_id': foreign_currency_2.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 3000.00, 'currency_id': foreign_currency_2.id},
        ])
        self.assertRecordValues(all_expenses.account_move_id.origin_payment_id.sorted('id'), [
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_1.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
        ])

    #############################################
    #  Test Corner Cases
    #############################################

    def test_expense_company_dates(self):
        expenses = self.create_expenses([
            {
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 350.00,
                'payment_mode': 'company_account',
                'date': '2024-01-01',
            },
            {
                'name': 'Lunch expense',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 90.00,
                'payment_mode': 'company_account',
                'date': '2024-01-12',
            },
        ]).sorted()  # By date desc

        expenses.action_submit()
        expenses.action_approve()
        expenses.action_post()

        move_twelve_january, move_first_january = expenses.account_move_id.sorted() # By date desc

        self.assertEqual(
            move_twelve_january.date,
            fields.Date.to_date('2024-01-12'),
            'move date should be the same as the expense date'
        )
        self.assertEqual(
            move_first_january.date,
            fields.Date.to_date('2024-01-01'),
            'move date should be the same as the expense date'
        )
        self.assertTrue(90 == move_twelve_january.amount_total == move_twelve_january.origin_payment_id.amount)
        self.assertTrue(350 == move_first_january.amount_total == move_first_january.origin_payment_id.amount)
        self.assertRecordValues(expenses, [
            {'date': fields.Date.from_string('2024-01-12'), 'total_amount':  90.00, 'state': 'paid'},
            {'date': fields.Date.from_string('2024-01-01'),'total_amount': 350.00, 'state': 'paid'},
        ])

    def test_corner_case_defaults_values_from_product(self):
        """ As soon as you set a product, the expense name, uom, taxes and account are set according to the product. """
        # Disable multi-uom
        self.env.ref('base.group_user').implied_ids -= self.env.ref('uom.group_uom')
        self.expense_user_employee.group_ids -= self.env.ref('uom.group_uom')

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
        self.assertEqual(expense.tax_ids, product.supplier_taxes_id.filtered(lambda t: t.company_id == expense.company_id))
        self.assertEqual(expense.account_id, product._get_product_accounts()['expense'])

    def test_attachments_in_move_from_own_expense(self):
        """ Checks that journal entries created form expense reports paid by employee have a copy of the attachments in the expense. """
        expense = self.create_expenses({'name': 'Employee expense'})
        expense_2 = self.create_expenses({'name': 'Employee expense 2'})
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

        expenses.action_submit()
        expenses._do_approve()  # Skip duplicate wizard
        self.post_expenses_with_wizard(expenses)

        self.assertRecordValues(expenses.account_move_id.attachment_ids.sorted('name'), [
            {
                'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
                'name': 'file1.png',
                'res_model': 'account.move',
                'res_id': expense.account_move_id.id,
            },
            {
                'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
                'name': 'file2.png',
                'res_model': 'account.move',
                'res_id': expense_2.account_move_id.id,
            }
        ])

    def test_attachments_in_move_from_company_expense(self):
        """ Checks that journal entries created form expense reports paid by company have a copy of the attachments in the expense. """
        expense = self.create_expenses({
            'name': 'Company expense',
            'payment_mode': 'company_account',
        })
        expense_2 = self.create_expenses({
            'name': 'Company expense 2',
            'payment_mode': 'company_account',
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

        expenses.action_submit()
        expenses._do_approve()  # Skip duplicate wizard
        expenses.action_post()

        expense_move = expense.account_move_id
        expense_2_move = expense_2.account_move_id
        self.assertRecordValues(expense_move.attachment_ids, [{
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file1.png',
            'res_model': 'account.move',
            'res_id': expense_move.id
        }])

        self.assertRecordValues(expense_2_move.attachment_ids, [{
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file2.png',
            'res_model': 'account.move',
            'res_id': expense_2_move.id
        }])

    def test_expense_payment_method(self):
        default_payment_method_line = self.company_data['default_journal_bank'].outbound_payment_method_line_ids[0]
        check_method = self.env['account.payment.method'].sudo().create({
            'name': 'Print checks',
            'code': 'check_printing_expense_test',
            'payment_type': 'outbound',
        })
        new_payment_method_line = self.env['account.payment.method.line'].create({
            'name': 'Check',
            'payment_method_id': check_method.id,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_account_id': self.inbound_payment_method_line.payment_account_id.id,
        })

        expense = self.create_expenses({
            'payment_method_line_id': default_payment_method_line.id,
            'payment_mode': 'company_account',
        })

        self.assertRecordValues(expense, [{'payment_method_line_id': default_payment_method_line.id}])
        expense.payment_method_line_id = new_payment_method_line

        expense.action_submit()
        expense.action_approve()
        expense.action_post()
        self.assertRecordValues(expense.account_move_id.origin_payment_id, [{'payment_method_line_id': new_payment_method_line.id}])

    @freeze_time('2024-01-01')
    def test_expense_vendor(self):
        """ This test will do a basic flow when a vendor is set on the expense """
        vendor_a = self.env['res.partner'].create({'name': 'Ruben'})
        expense = self.create_expenses({
            'payment_mode': 'company_account',
            'vendor_id': vendor_a.id,
        })
        expense.action_submit()
        expense.action_approve()
        expense.action_post()

        self.assertEqual(vendor_a.id, expense.account_move_id.line_ids.partner_id.id)

    def test_payment_edit_fields(self):
        """ Test that some payment fields cannot be modified once linked with an expense """
        expense = self.create_expenses({
            'payment_mode': 'company_account',
            'total_amount_currency': 1000.00,
        })
        expense.action_submit()
        expense.action_approve()
        expense.action_post()
        payment = expense.account_move_id.origin_payment_id

        with self.assertRaises(UserError, msg="Cannot edit payment amount after linking to an expense"):
            payment.write({'amount': 500})

        payment.write({'is_sent': True})

    def test_corner_case_expense_submitted_cannot_be_zero(self):
        """
        Test that the expenses are not submitted if the total amount is 0.0 nor able to be edited that way
        unless unlinking it from the expense.
        """
        expense = self.create_expenses({'total_amount': 0.0, 'total_amount_currency': 0.0})

        # CASE 1: FORBIDS Trying to submit an expense with a total_amount(_currency) of 0.0
        with self.assertRaises(UserError):
            expense.action_submit()

        # CASE 2: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense is submitted to the manager
        expense.total_amount_currency = 1000
        expense.action_submit()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 3: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense is approved
        expense.action_approve()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 4: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense is posted and the account move created
        self.post_expenses_with_wizard(expense)
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 5: ALLOWS Changing the total_amount(_currency) to 0.0 when the expense is reset to draft
        expense.account_move_id.button_draft()
        expense.account_move_id.unlink()
        expense.action_reset()
        expense.write({'total_amount_currency': 0.0, 'total_amount': 0.0})

        # CASE 6: FORBIDS Setting the amounts to 0 while submitting the expense
        expense.write({'total_amount_currency': 1000.0, 'total_amount': 1000.0})
        with self.assertRaises(UserError):
            expense.write({'total_amount_currency': 0.0, 'state': 'submitted'})
        with self.assertRaises(UserError):
            expense.write({'total_amount': 0.0, 'state': 'submitted'})

        # CASE 7: ALLOWS Setting the amounts to 0 while resetting the expense to draft
        expense.write({'total_amount_currency': 0.0, 'total_amount': 0.0, 'state': 'draft'})

    def test_foreign_currencies_total(self):
        """ Check that the dashboard computes amount properly in company currency """
        self.create_expenses([{
                'name': 'Company expense',
                'payment_mode': 'company_account',
                'total_amount_currency': 1000.00,
                'employee_id': self.expense_employee.id,
            },
            {
                'name': 'Employee expense',
                'payment_mode': 'own_account',
                'currency_id': self.other_currency.id,
                'total_amount_currency': 1000.00,
                'total_amount': 2000.00,
                'employee_id': self.expense_employee.id,
            },
        ])
        expense_data = self.env['hr.expense'].with_user(self.expense_user_employee).get_expense_dashboard()
        self.assertEqual(expense_data['draft']['amount'], 3000.00)

    def test_update_expense_price_on_product_standard_price(self):
        """
        Tests that updating the standard price of a product will update all the un-submitted
        expenses using that product as a category.
        """
        product = self.env['product.product'].create({
            'name': 'Product',
            'standard_price': 100.0,
        })
        expenses = expense_no_update, expense_update = self.create_expenses([
            {'name': name, 'product_id': product.id, 'total_amount': 100.0}
            for name in ('test no update', 'test update')
        ]).sorted('name')

        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
            {'name':    'test update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
        ])
        expense_no_update.action_submit()  # No update when the expense is submitted

        product.standard_price = 200.0
        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit': 100.0, 'quantity': 1.0, 'total_amount': 100.0},
            {'name':    'test update', 'price_unit': 200.0, 'quantity': 1.0, 'total_amount': 200.0},  # total is updated
        ])

        expense_update.quantity = 5
        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount':  100.0},
            {'name':    'test update', 'price_unit': 200.0, 'quantity': 5, 'total_amount': 1000.0},  # total is updated
        ])

        product.standard_price = 0.0
        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit':  100.0, 'quantity': 1, 'total_amount':  100.0},
            {'name':    'test update', 'price_unit': 1000.0, 'quantity': 1, 'total_amount': 1000.0},  # quantity & price_unit only are updated
        ])

        expenses.action_submit()  # This expense should not be updated any more
        product.standard_price = 300.0
        self.assertRecordValues(expenses.sorted('name'), [
            {'name': 'test no update', 'price_unit':  100.0, 'quantity': 1, 'total_amount':  100.0},
            {'name':    'test update', 'price_unit': 1000.0, 'quantity': 1, 'total_amount': 1000.0},  # no update
        ])

    def test_expense_standard_price_update_warning(self):
        expense_cat_A = self.env['product.product'].create({
            'name': 'Category A',
            'default_code': 'CA',
            'standard_price': 0.0,
        })
        expense_cat_B = self.env['product.product'].create({
            'name': 'Category B',
            'default_code': 'CB',
            'standard_price': 0.0,
        })
        expense_cat_C = self.env['product.product'].create({
            'name': 'Category C',
            'default_code': 'CC',
            'standard_price': 0.0,
        })
        self.create_expenses([
            {
                'name': 'Expense 1',
                'product_id': expense_cat_A.id,
                'total_amount': 1,
            },
            {
                'name': 'Expense 2',
                'product_id': expense_cat_B.id,
                'total_amount': 5,
            },
        ])

        # At first, there is no warning message on the categories because their prices are 0
        self.assertFalse(expense_cat_A.standard_price_update_warning)
        self.assertFalse(expense_cat_B.standard_price_update_warning)
        self.assertFalse(expense_cat_C.standard_price_update_warning)

        # When modifying the price of the first category, a message should appear as a an expense will be modified.
        with Form(expense_cat_A, view="hr_expense.product_product_expense_form_view") as form:
            form.standard_price = 5
            self.assertTrue(form.standard_price_update_warning)

        # When modifying the price of the second category, no message should appear as the price of the linked
        # expense is the price of the category that is going to be saved.
        with Form(expense_cat_B, view="hr_expense.product_product_expense_form_view") as form:
            form.standard_price = 5
            self.assertFalse(form.standard_price_update_warning)

        # When modifying the price of the their category, no message should appear as no expense is linked to it.
        with Form(expense_cat_C, view="hr_expense.product_product_expense_form_view") as form:
            form.standard_price = 5
            self.assertFalse(form.standard_price_update_warning)

    def test_compute_standard_price_update_warning_product_with_and_without_expense(self):
        """
        Test that the compute doesn't raise an error with mixed recordsets (products used in expenses and not used in expenses)
        """
        product_expensed = self.env['product.product'].create({
            'name': 'Category A',
            'default_code': 'CA',
            'standard_price': 0.0,
        })
        product_not_expensed = self.env['product.product'].create({
            'name': 'Category B',
            'default_code': 'CB',
            'standard_price': 0.0,
        })
        self.env['hr.expense'].create({
            'employee_id': self.expense_employee.id,
            'name': 'Expense 1',
            'product_id': product_expensed.id,
            'total_amount': 1,
        })

        (product_expensed | product_not_expensed)._compute_standard_price_update_warning()

    def test_expense_multi_company(self):
        main_company = self.company_data['company']
        other_company = self.company_data_2['company']
        self.expense_employee.sudo().company_id = other_company

        # The expense employee is able to create an expense for company_2.
        # product_a needs a standard_price in company_2
        self.product_a.with_context(allowed_company_ids=self.company_data_2['company'].ids).standard_price = 100

        Expense = self.env['hr.expense'].with_user(self.expense_user_employee).with_context(allowed_company_ids=other_company.ids)
        expense_approve = Expense.create([{
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'date': '2016-01-01',
            'product_id': self.product_a.id,
            'quantity': 1200.0,
        }])
        expense_refuse = Expense.create([{
            'name': 'Second Expense for employee',
            'employee_id': self.expense_employee.id,
            'date': '2016-01-01',
            'product_id': self.product_a.id,
            'quantity': 1000.0,
        }])
        expenses = expense_approve | expense_refuse
        self.assertRecordValues(expenses, [
            {'company_id': self.company_data_2['company'].id},
            {'company_id': self.company_data_2['company'].id},
        ])

        # The expense employee is able to submit the expense.
        expenses.with_user(self.expense_user_employee).action_submit()

        # An expense manager is not able to approve nor refuse without access to company_2.
        with self.assertRaises(UserError):
            expense_approve \
                .with_user(self.expense_user_manager) \
                .with_context(allowed_company_ids=main_company.ids, company_id=main_company.id) \
                .action_approve()

        with self.assertRaises(UserError):
            expense_refuse \
                .with_user(self.expense_user_manager) \
                .with_context(allowed_company_ids=main_company.ids) \
                ._do_refuse('failed')

        # An expense manager is able to approve/refuse with access to company_2.
        expense_approve \
            .with_user(self.expense_user_manager) \
            .with_context(allowed_company_ids=other_company.ids) \
            .action_approve()
        expense_refuse \
            .with_user(self.expense_user_manager) \
            .with_context(allowed_company_ids=other_company.ids) \
            ._do_refuse('failed')

        # An expense manager having accounting access rights is not able to post the journal entry without access
        # to company_2.
        with self.assertRaises(UserError):
            self.post_expenses_with_wizard(expense_approve.with_user(self.env.user).with_context(allowed_company_ids=main_company.ids))

        # An expense manager having accounting access rights is able to post the journal entry with access to
        # company_2.
        self.post_expenses_with_wizard(expense_approve.with_user(self.env.user).with_context(allowed_company_ids=other_company.ids))

    def test_tax_is_used_when_in_transactions(self):
        """ Ensures that a tax is set to used when it is part of some transactions """
        # Account.move is one type of transaction
        tax_expense = self.env['account.tax'].create({
            'name': 'test_is_used_expenses',
            'amount': '100',
            'include_base_amount': True,
        })

        self.create_expenses({'tax_ids': [Command.set(tax_expense.ids)]})
        tax_expense.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_expense.is_used)

    def test_expense_by_company_with_caba_tax(self):
        """ When using cash basis tax in an expense paid by the company, the transition account should not be used. """

        caba_tag = self.env['account.account.tag'].create({
            'name': 'Cash Basis Tag Final Account',
            'applicability': 'taxes',
        })
        caba_transition_account = self.env['account.account'].create({
            'name': 'Cash Basis Tax Transition Account',
            'account_type': 'asset_current',
            'code': '131001',
            'reconcile': True,
        })
        caba_tax = self.env['account.tax'].create({
            'name': 'Cash Basis Tax',
            'tax_exigibility': 'on_payment',
            'amount': 15,
            'cash_basis_transition_account_id': caba_transition_account.id,
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': caba_tag.ids,
                }),
            ]
        })

        expense = self.create_expenses({
            'payment_mode': 'company_account',
            'tax_ids': [Command.set(caba_tax.ids)],
        })
        expense.action_submit()
        expense.action_approve()
        expense.action_post()
        moves = expense.account_move_id
        tax_lines = moves.line_ids.filtered(lambda line: line.tax_line_id == caba_tax)
        self.assertNotEqual(tax_lines.account_id, caba_transition_account, "The tax should not be on the transition account")
        self.assertEqual(tax_lines.tax_tag_ids, caba_tag, "The tax should still retrieve its tags")

    def test_expense_mandatory_analytic_plan_product_category(self):
        """
        Check that when an analytic plan has a mandatory applicability matching
        product category this is correctly triggered
        """
        self.env['account.analytic.applicability'].create({
            'business_domain': 'expense',
            'analytic_plan_id': self.analytic_plan.id,
            'applicability': 'mandatory',
            'product_categ_id': self.product_a.categ_id.id,
        })

        expense = self.create_expenses({
            'product_id': self.product_a.id,
            'quantity': 350.00,
            'payment_mode': 'company_account',
        })

        expense.action_submit()
        with self.assertRaises(ValidationError, msg="One or more lines require a 100% analytic distribution."):
            expense.with_context(validate_analytic=True).action_approve()
        expense.analytic_distribution = {self.analytic_account_1.id: 100.00}
        expense.with_context(validate_analytic=True).action_approve()

    def test_expense_no_stealing_from_employees(self):
        """
        Test to check that the company doesn't steal their employee when the commercial_partner_id of the employee partner
        is the company
        """
        self.expense_employee.user_partner_id.parent_id = self.env.company.partner_id
        self.assertEqual(self.env.company.partner_id, self.expense_employee.user_partner_id.commercial_partner_id)

        expense = self.create_expenses({'employee_id': self.expense_employee.id})
        expense.action_submit()
        expense.action_approve()
        self.post_expenses_with_wizard(expense)
        move = expense.account_move_id

        self.assertNotEqual(move.commercial_partner_id, self.env.company.partner_id)
        self.assertEqual(move.partner_id, self.expense_employee.user_partner_id)
        self.assertEqual(move.commercial_partner_id, self.expense_employee.user_partner_id)

    def test_expense_set_total_amount_to_0(self):
        """ Checks that amount fields are correctly updating when setting total_amount to 0 """
        expense = self.create_expenses({
            'product_id': self.product_c.id,
            'total_amount_currency': 100.0,
        })
        expense.total_amount_currency = 0.0
        self.assertTrue(expense.currency_id.is_zero(expense.tax_amount))
        self.assertTrue(expense.company_currency_id.is_zero(expense.total_amount))

    def test_expense_set_quantity_to_0(self):
        """ Checks that amount fields except for unit_amount are correctly updating when setting quantity to 0 """
        expense = self.create_expenses({
            'product_id': self.product_b.id,
            'quantity': 10
        })
        expense.quantity = 0
        self.assertTrue(expense.currency_id.is_zero(expense.total_amount_currency))
        self.assertEqual(expense.company_currency_id.compare_amounts(expense.price_unit, self.product_b.standard_price), 0)

    def test_employee_expense_in_foreign_currency(self):
        """ Checks that the currency of the posted entries is always the company currency """
        expense = self.create_expenses({
            'payment_mode': 'own_account',
            'currency_id': self.other_currency.id,
        })
        expense.action_submit()
        expense.action_approve()
        expense._post_without_wizard()
        self.assertRecordValues(
            expense.account_move_id,
            [{'amount_total': 500.0, 'currency_id': expense.account_move_id.company_currency_id.id}],
        )
