# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from freezegun import freeze_time

from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.exceptions import UserError
from odoo.tests import tagged, Form
from odoo.tools.misc import formatLang


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
            - accounting_date computation and override
            - price_unit, total_amount_currency and quantity computation
            - Split payments into one payment per expense when paid by company
            - Override account on expense
            - Payment states and payment terms
            - Unlinking payments reverts to approved state
            - Cannot delete an analytic account if linked to an expense
        """
        # pylint: disable=bad-whitespace
        self.expense_employee.user_partner_id.property_supplier_payment_term_id = self.env.ref('account.account_payment_term_30days')
        expense_sheet_by_employee = self.create_expense_report({
            'name': 'Expense for John Smith',
            'accounting_date': '2021-10-10',  # This should be the date set as the accounting_date
            'expense_line_ids': [Command.create({
                'name': 'PA 2*800 + 15%',  # Taxes are included
                'employee_id': self.expense_employee.id,
                'account_id': self.expense_account.id,  # Test with a specific account override
                'product_id': self.product_a.id,
                'quantity': 2,
                'payment_mode': 'own_account',
                'company_id': self.company_data['company'].id,
                'date': '2021-10-11',
                'analytic_distribution': {self.analytic_account_1.id: 100},
            }), Command.create({
                'name': 'PB 160 + 2*15%',  # Taxes are included
                'employee_id': self.expense_employee.id,
                'product_id': self.product_b.id,
                'payment_mode': 'own_account',
                'company_id': self.company_data['company'].id,
                'date': '2021-10-13',
                'analytic_distribution': {self.analytic_account_2.id: 100},
            })],
        })
        expense_sheet_by_company = self.create_expense_report({
            'name': 'Expense for Company',
            'employee_id': self.expense_employee.id,
            'expense_line_ids': [Command.create({
                'name': 'PC 1000 + 15%',  # Taxes are included
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': '2021-10-11',
                'payment_mode': 'company_account',
                'company_id': self.company_data['company'].id,
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            }), Command.create({
                'name': 'PB 160 + 2*15% 2',  # Taxes are included
                'employee_id': self.expense_employee.id,
                'product_id': self.product_b.id,
                'payment_mode': 'company_account',
                'company_id': self.company_data['company'].id,
                'date': '2021-10-12',  # This should be the date set as the accounting_date
            })],
        })
        expense_sheets = expense_sheet_by_employee | expense_sheet_by_company

        # Checking expense sheets values at creation
        self.assertRecordValues(expense_sheets, [
            {'total_amount': 1760.00, 'untaxed_amount': 1514.38, 'total_tax_amount': 245.62, 'state': 'draft', 'accounting_date': date(2021, 10, 10)},
            {'total_amount': 1160.00, 'untaxed_amount':  992.65, 'total_tax_amount': 167.35, 'state': 'draft', 'accounting_date': False},
        ])
        self.assertRecordValues(expense_sheets.expense_line_ids, [
            {'total_amount_currency': 1600.00, 'untaxed_amount_currency': 1391.30, 'price_unit':  800.00, 'tax_amount': 208.70, 'state': 'reported'},
            {'total_amount_currency':  160.00, 'untaxed_amount_currency':  123.08, 'price_unit':  160.00, 'tax_amount':  36.92, 'state': 'reported'},
            {'total_amount_currency': 1000.00, 'untaxed_amount_currency':  869.57, 'price_unit': 1000.00, 'tax_amount': 130.43, 'state': 'reported'},
            {'total_amount_currency':  160.00, 'untaxed_amount_currency':  123.08, 'price_unit':  160.00, 'tax_amount':  36.92, 'state': 'reported'},
        ])

        # Submitting properly change states
        expense_sheets.action_submit_sheet()
        self.assertRecordValues(expense_sheets, [
            {'state': 'submit'},
            {'state': 'submit'},
        ])
        self.assertRecordValues(expense_sheets.expense_line_ids, [
            {'state': 'submitted'},
            {'state': 'submitted'},
            {'state': 'submitted'},
            {'state': 'submitted'},
        ])

        # Approving properly change states
        expense_sheets.action_approve_expense_sheets()
        self.assertRecordValues(expense_sheets, [
            {'state': 'approve'},
            {'state': 'approve'},
        ])
        self.assertRecordValues(expense_sheets.expense_line_ids, [
            {'state': 'approved'},
            {'state': 'approved'},
            {'state': 'approved'},
            {'state': 'approved'},
        ])

        # Generate a payment for 'company_account' (and its move(s)) and a vendor bill for 'own_account'
        expense_sheets.action_sheet_move_create()
        self.assertRecordValues(expense_sheets, [
            {'state': 'post', 'payment_state': 'not_paid', 'accounting_date': date(2021, 10, 10)},
            {'state': 'done', 'payment_state': 'paid',     'accounting_date': date(2021, 10, 12)},  # Set to paid as move is posted directly
        ])
        self.assertRecordValues(expense_sheets.expense_line_ids, [
            {'payment_mode': 'own_account',     'state': 'approved'},  # vv
            {'payment_mode': 'own_account',     'state': 'approved'},  # As the payment is not done yet those are still in "approved"
            {'payment_mode': 'company_account', 'state': 'done'},
            {'payment_mode': 'company_account', 'state': 'done'},
        ])
        # One payment for the whole sheet if 'own_account'
        expected_partner_id = self.expense_user_employee.partner_id.id
        self.assertRecordValues(expense_sheet_by_employee.account_move_ids, [{
            'amount_total': 1760.00,
            'ref': 'Expense for John Smith',
            'date': date(2021, 10, 10),
            'invoice_date_due': date(2021, 11, 9),  # The due date is the one set for the partner
            'partner_id': expected_partner_id
        },
        ])
        # One payment per expense if 'company_account'
        self.assertRecordValues(expense_sheet_by_company.account_move_ids, [
            {'amount_total': 1000.00, 'ref': 'PC 1000 + 15%',    'date': date(2021, 10, 12), 'partner_id': False},
            {'amount_total':  160.00, 'ref': 'PB 160 + 2*15% 2', 'date': date(2021, 10, 12), 'partner_id': False},
        ])
        tax_account_id = self.company_data['default_account_tax_purchase'].id
        default_account_payable_id = self.company_data['default_account_payable'].id
        product_b_account_id = self.product_b.property_account_expense_id.id
        product_c_account_id = self.product_c.property_account_expense_id.id
        company_payment_account_id = self.company_data['company'].account_journal_payment_credit_account_id.id
        # One payment per expense
        self.assertRecordValues(expense_sheets.account_move_ids.line_ids, [
            # own_account expense sheet move
            {'balance':   123.08, 'account_id': product_b_account_id,       'name': 'expense_employee: PB 160 + 2*15%',   'date': date(2021, 10, 10)},
            {'balance':  1391.30, 'account_id': self.expense_account.id,    'name': 'expense_employee: PA 2*800 + 15%',   'date': date(2021, 10, 10)},
            {'balance':    18.46, 'account_id': tax_account_id,             'name': '15%',                                'date': date(2021, 10, 10)},
            {'balance':    18.46, 'account_id': tax_account_id,             'name': '15% (Copy)',                         'date': date(2021, 10, 10)},
            {'balance':   208.70, 'account_id': tax_account_id,             'name': '15%',                                'date': date(2021, 10, 10)},
            {'balance': -1760.00, 'account_id': default_account_payable_id, 'name': False,                                'date': date(2021, 10, 10)},

            # company_account expense 1 move
            {'balance':   869.57, 'account_id': product_c_account_id,       'name': 'expense_employee: PC 1000 + 15%',    'date': date(2021, 10, 12)},
            {'balance':   130.43, 'account_id': tax_account_id,             'name': '15%',                                'date': date(2021, 10, 12)},
            {'balance': -1000.00, 'account_id': company_payment_account_id, 'name': 'expense_employee: PC 1000 + 15%',    'date': date(2021, 10, 12)},

            # company_account expense 2 move
            {'balance':  123.08, 'account_id': product_b_account_id,        'name': 'expense_employee: PB 160 + 2*15% 2', 'date': date(2021, 10, 12)},
            {'balance':   18.46, 'account_id': tax_account_id,              'name': '15%',                                'date': date(2021, 10, 12)},
            {'balance':   18.46, 'account_id': tax_account_id,              'name': '15% (Copy)',                         'date': date(2021, 10, 12)},
            {'balance': -160.00, 'account_id': company_payment_account_id,  'name': 'expense_employee: PB 160 + 2*15% 2', 'date': date(2021, 10, 12)},
        ])

        # Own_account partial payment
        payment_1 = self.get_new_payment(expense_sheet_by_employee, 1700.0)
        liquidity_lines1 = payment_1._seek_for_lines()[0]
        self.assertRecordValues(expense_sheet_by_employee, [{'payment_state': 'partial', 'state': 'done'}])

        # own_account remaining payment
        payment_2 = self.get_new_payment(expense_sheet_by_employee, 60.0)
        liquidity_lines2 = payment_2._seek_for_lines()[0]
        in_payment_state = expense_sheet_by_employee.account_move_ids._get_invoice_in_payment_state()
        self.assertRecordValues(expense_sheet_by_employee, [{'payment_state': in_payment_state, 'state': 'done'}])
        self.assertRecordValues(expense_sheet_by_employee.expense_line_ids, [{'state': 'done'}] * 2)

        # Reconciling own_account
        statement_line = self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ref': 'pay_ref',
            'amount': -1760.0,
            'partner_id': self.expense_employee.work_contact_id.id,
        })

        # Reconcile without the bank reconciliation widget since the widget is in enterprise.
        _trash, st_suspense_lines, _trash = statement_line.with_context(skip_account_move_synchronization=True)._seek_for_lines()
        st_suspense_lines.account_id = liquidity_lines1.account_id
        (st_suspense_lines + liquidity_lines1 + liquidity_lines2).reconcile()
        self.assertRecordValues(expense_sheet_by_employee, [{'payment_state': 'paid', 'state': 'done'}])

        # Trying to delete analytic accounts should be forbidden if linked to an expense
        with self.assertRaises(UserError):
            (self.analytic_account_1 | self.analytic_account_2).unlink()

        # Unlinking moves
        (payment_1 | payment_2).action_draft()
        self.assertRecordValues(expense_sheet_by_employee, [{'payment_state': 'not_paid', 'state': 'post'}])
        expense_sheet_by_employee.account_move_ids.button_draft()
        expense_sheet_by_employee.account_move_ids.unlink()

        with self.assertRaises(UserError, msg="For company-paid expenses report, deleting payments is an all-or-nothing situation"):
            expense_sheet_by_company.account_move_ids[:-1].payment_id.unlink()
        expense_sheet_by_company.account_move_ids.payment_id.unlink()

        self.assertRecordValues(expense_sheets.sorted('payment_mode'), [
            {'payment_mode': 'company_account', 'state': 'approve', 'payment_state': 'not_paid', 'account_move_ids': []},
            {'payment_mode': 'own_account',     'state': 'approve', 'payment_state': 'not_paid', 'account_move_ids': []},
        ])

        expense_sheet_by_employee.action_reset_expense_sheets()
        self.assertRecordValues(expense_sheet_by_employee, [{'state': 'draft', 'payment_state': 'not_paid', 'account_move_ids': []}])
        expense_sheet_by_employee.expense_line_ids.unlink()
        # Only possible if no expense linked to the account
        self.analytic_account_1.unlink()

    def test_expense_split_flow(self):
        """ Check Split Expense flow. """
        expense = self.create_expense({'analytic_distribution': {self.analytic_account_1.id: 100}})

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

        # Grant Analytic Accounting rights, to be able to modify analytic_distribution from the wizard
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

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
            }, {
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'product_id': expense.product_id.id,
                'total_amount_currency': 300.00,
                'tax_ids': [self.tax_purchase_a.id],
                'tax_amount_currency': 39.13,
                'untaxed_amount_currency': 260.87,
                'analytic_distribution': {str(self.analytic_account_1.id): 100},
            }, {
                'name': expense.name,
                'employee_id': expense.employee_id.id,
                'product_id': expense.product_id.id,
                'total_amount_currency': 500.00,
                'tax_ids': [self.tax_purchase_a.id, self.tax_purchase_b.id],
                'tax_amount_currency': 115.38,
                'untaxed_amount_currency': 384.62,
                'analytic_distribution': {str(self.analytic_account_2.id): 100},
            }
        ])

    #############################################
    #  Test Multi-currency
    #############################################

    def test_expense_multi_currencies(self):
        """
        Checks that the currency rate is recomputed properly when the total in company currency is set to a new value
        and that extreme rounding cases do not end up with non-consistend data
        """
        # pylint: disable=bad-whitespace
        foreign_currency_1 = self.currency_data['currency']
        foreign_currency_2, foreign_currency_3 = self.env['res.currency'].create([{
                'name': 'Ex1',
                'symbol': ' ',
                'rounding': 0.01,
                'position': 'after',
                'currency_unit_label': 'Nothing',
                'currency_subunit_label': 'Smaller Nothing',
            }, {
                'name': 'Ex2',
                'symbol': '  ',
                'rounding': 0.01,
                'position': 'after',
                'currency_unit_label': 'Nothing 2',
                'currency_subunit_label': 'Smaller Nothing 2',
            },
        ])
        self.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 1 / 1.52,
            'currency_id': foreign_currency_2.id,
            'company_id': self.company_data['company'].id,
        })
        self.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 1 / 0.148431,
            'currency_id': foreign_currency_3.id,
            'company_id': self.company_data['company'].id,
        })
        foreign_sale_journal = self.company_data['default_journal_sale'].copy()
        foreign_sale_journal.currency_id = foreign_currency_2.id
        expense_sheet_currency_mix_1 = self.create_expense_report({
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.create({
            'payment_mode': 'company_account',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount_currency': 1000.00,
            'date': self.frozen_today,
            'company_id': self.company_data['company'].id,
            'currency_id': foreign_currency_1.id,  # rate is 1:2
            'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            })],
        })
        expense_sheet_currency_mix_2 = self.create_expense_report({
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.create({
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'currency_id': foreign_currency_2.id,  # rate is 1:1.52
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            }), Command.create({
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'currency_id': foreign_currency_2.id,  # rate is 1:1.52
                'tax_ids': [Command.set((self.tax_purchase_a.id, self.tax_purchase_b.id))],
            })],
        })
        expense_sheet_currency_mix_3 = self.create_expense_report({
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.create({
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'currency_id': foreign_currency_2.id,  # rate is 1:1.52
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            }), Command.create({
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'currency_id': foreign_currency_1.id,  # rate is 1:2
                'tax_ids': [Command.set((self.tax_purchase_a.id, self.tax_purchase_b.id))],
            })],
        })
        expense_sheet_currency_mix_4 = self.create_expense_report({  # This case handles a direct override in back-end of the rate
            'journal_id': foreign_sale_journal.id,
            'expense_line_ids': [Command.create({
                'payment_mode': 'company_account',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount_currency': 1000.00,
                'total_amount': 3000.00,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'currency_id': foreign_currency_2.id,  # default rate is 1:1.52, overriden to 3
                'tax_ids': [Command.set(self.tax_purchase_a.ids)],
            })],
        })
        expenses_sheet_currencies_mix = expense_sheet_currency_mix_1 | expense_sheet_currency_mix_2 \
                                         | expense_sheet_currency_mix_3 | expense_sheet_currency_mix_4
        self.assertRecordValues(expenses_sheet_currencies_mix.expense_line_ids, [
            # Sheet 1, mono foreign currency
            {'currency_rate': 0.50, 'total_amount_currency': 1000.00, 'total_amount':  500.00, 'currency_id': foreign_currency_1.id},
            # Sheet 2, multiple identical foreign currencies
            {'currency_rate': 1.52, 'total_amount_currency': 1000.00, 'total_amount': 1520.00, 'currency_id': foreign_currency_2.id},
            {'currency_rate': 1.52, 'total_amount_currency': 1000.00, 'total_amount': 1520.00, 'currency_id': foreign_currency_2.id},
            # Sheet 3, multiple different foreign currencies
            {'currency_rate': 1.52, 'total_amount_currency': 1000.00, 'total_amount': 1520.00, 'currency_id': foreign_currency_2.id},
            {'currency_rate': 0.50, 'total_amount_currency': 1000.00, 'total_amount':  500.00, 'currency_id': foreign_currency_1.id},
            # Sheet 4, mono foreign currencies already overriden
            {'currency_rate': 3.00, 'total_amount_currency': 1000.00, 'total_amount': 3000.00, 'currency_id': foreign_currency_2.id},
        ])

        # Manually changing rate on the two first expenses after creation to check they recompute properly
        # Back-end override
        expense_sheet_currency_mix_1.expense_line_ids[0].write({'total_amount': 1000.00})

        # Front-end override
        expense = expense_sheet_currency_mix_2.expense_line_ids[0]
        with Form(expense) as expense_form:
            expense_form.total_amount = 2000.00

        self.assertRecordValues(expenses_sheet_currencies_mix.expense_line_ids.sorted('id'), [
            {'currency_rate': 1.00, 'total_amount_currency': 1000.00, 'total_amount': 1000.00},  # Rate should change
            {'currency_rate': 2.00, 'total_amount_currency': 1000.00, 'total_amount': 2000.00},  # Rate should change
            {'currency_rate': 1.52, 'total_amount_currency': 1000.00, 'total_amount': 1520.00},  # Rate should NOT change
            {'currency_rate': 1.52, 'total_amount_currency': 1000.00, 'total_amount': 1520.00},  # Rate should NOT change
            {'currency_rate': 0.50, 'total_amount_currency': 1000.00, 'total_amount':  500.00},  # Rate should NOT change
            {'currency_rate': 3.00, 'total_amount_currency': 1000.00, 'total_amount': 3000.00},  # Rate should not revert to the default one (1.52)
        ])

        # Sheet and move creation should not touch the rates anymore
        expenses_sheet_currencies_mix.action_submit_sheet()
        expenses_sheet_currencies_mix.action_approve_expense_sheets()
        expenses_sheet_currencies_mix.action_sheet_move_create()
        self.assertRecordValues(expenses_sheet_currencies_mix.account_move_ids, [
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1000.00, 'currency_id': foreign_currency_1.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 2000.00, 'currency_id': foreign_currency_2.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1520.00, 'currency_id': foreign_currency_2.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1520.00, 'currency_id': foreign_currency_2.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed':  500.00, 'currency_id': foreign_currency_1.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 3000.00, 'currency_id': foreign_currency_2.id},
        ])
        self.assertRecordValues(expenses_sheet_currencies_mix.account_move_ids.payment_id, [
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_1.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_1.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
        ])

        # Test that the roundings are consistent no matter by whom it is paid
        expense_values = {
                'payment_mode': 'company_account',
                'total_amount_currency': 100.00,
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'currency_id': foreign_currency_3.id,  # rate is 1:0.148431
                'tax_ids': [Command.set((self.tax_purchase_a.id, self.tax_purchase_b.id))],
            }
        expense_sheet_company_rounding = self.create_expense_report({'expense_line_ids': [Command.create(expense_values)]})
        del expense_values['payment_mode'] # Sets the default payment_mode (own_account)
        expense_sheet_employee_rounding = self.create_expense_report({'expense_line_ids': [Command.create(expense_values)]})
        expense_sheets_rounding = expense_sheet_company_rounding | expense_sheet_employee_rounding
        self.assertRecordValues(expense_sheets_rounding.expense_line_ids, [
            {'untaxed_amount_currency': 76.92, 'total_amount_currency': 100.00, 'total_amount': 14.84, 'tax_amount_currency': 23.08, 'tax_amount': 3.42},
            {'untaxed_amount_currency': 76.92, 'total_amount_currency': 100.00, 'total_amount': 14.84, 'tax_amount_currency': 23.08, 'tax_amount': 3.42},
        ])

        expense_sheets_rounding.action_submit_sheet()
        expense_sheets_rounding.action_approve_expense_sheets()
        expense_sheets_rounding.action_sheet_move_create()

        self.assertRecordValues(expense_sheets_rounding.account_move_ids.line_ids, [
            {'balance':  11.42, 'amount_currency':   76.92},
            {'balance':   1.71, 'amount_currency':   11.54},  # == 3.42 tax_amount & 23.08 tax_amount
            {'balance':   1.71, 'amount_currency':   11.54},
            {'balance': -14.84, 'amount_currency': -100.00},

            {'balance':  11.42, 'amount_currency':  11.42},  # Paid by employee so converted into company_currency
            {'balance':   1.71, 'amount_currency':   1.71},  # == 3.42 tax_amount
            {'balance':   1.71, 'amount_currency':   1.71},
            {'balance': -14.84, 'amount_currency': -14.84},
        ])

    #############################################
    #  Test Corner Cases
    #############################################
    def test_expense_corner_case_changing_employee(self):
        """
        Test changing an employee on the expense that is linked with the sheet.
            - In case sheet has only one expense linked with it, than changing an employee on expense should trigger changing an employee
              on the sheet itself.
            - In case sheet has more than one expense linked with it, than changing an employee on one of the expenses,
              should cause unlinking the expense from the sheet.
        """

        employee = self.env['hr.employee'].create({'name': 'Gabriel Iglesias'})
        expense_sheet_employee_1 = self.create_expense_report()  # default employee is self.expense_employee
        expense_employee_2 = self.create_expense({'employee_id': employee.id})

        expense_sheet_employee_1.expense_line_ids.employee_id = employee
        self.assertEqual(expense_sheet_employee_1.employee_id, employee, 'Employee should have changed on the sheet')

        expense_sheet_employee_1.expense_line_ids |= expense_employee_2
        expense_employee_2.employee_id = self.expense_employee.id
        self.assertEqual(expense_employee_2.sheet_id.id, False, 'Sheet should be unlinked from the expense')

    def test_expenses_corner_case_with_tax_and_lock_date(self):
        """ Test that when creating an expense move in a locked period still works but its accounting date is the current day """
        self.env.company.tax_lock_date = '2022-01-01'

        expense_sheet = self.create_expense_report({
            'name': 'Expense for John Smith',
            'accounting_date': '2020-01-01',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2020-01-02',
            })],
        })

        expense_sheet.action_submit_sheet()
        with freeze_time(self.frozen_today):
            expense_sheet.action_approve_expense_sheets()
            expense_sheet.action_sheet_move_create()
        self.assertEqual(expense_sheet.accounting_date, self.frozen_today)

    def test_corner_case_defaults_values_from_product(self):
        """ As soon as you set a product, the expense name, uom, taxes and account are set according to the product. """
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
            'total_amount_currency': 1000.00,
            'employee_id': self.expense_employee.id,
        })
        expense_2 = self.env['hr.expense'].create({
            'name': 'Company expense 2',
            'date': '2022-11-16',
            'payment_mode': 'company_account',
            'total_amount_currency': 1000.00,
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
            })

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Sheet test',
            'employee_id': self.expense_employee.id,
            'payment_method_line_id': default_payment_method_line.id,
            'expense_line_ids': [Command.create({
                'name': 'test payment_mode',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'payment_mode': 'company_account',
                'total_amount': 60,
                'tax_ids': [self.tax_purchase_a.id, self.tax_purchase_b.id],
            })],
        })

        self.assertRecordValues(expense_sheet, [{'payment_method_line_id': default_payment_method_line.id}])
        expense_sheet.payment_method_line_id = new_payment_method_line

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()
        self.assertRecordValues(expense_sheet.account_move_ids.payment_id, [{'payment_method_line_id': new_payment_method_line.id}])
