# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import date

from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tests import tagged, Form
from odoo.tools.misc import format_date


@tagged('-at_install', 'post_install')
class TestExpenses(TestExpenseCommon):
    #############################################
    #  Test Expense flows
    #############################################
    @freeze_time("2021-12-12")
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
            {'total_amount_currency': 1600.00, 'untaxed_amount_currency': 1391.30, 'price_unit':  800.00, 'tax_amount_currency': 208.70, 'state': 'reported'},
            {'total_amount_currency':  160.00, 'untaxed_amount_currency':  123.08, 'price_unit':  160.00, 'tax_amount_currency':  36.92, 'state': 'reported'},
            {'total_amount_currency': 1000.00, 'untaxed_amount_currency':  869.57, 'price_unit': 1000.00, 'tax_amount_currency': 130.43, 'state': 'reported'},
            {'total_amount_currency':  160.00, 'untaxed_amount_currency':  123.08, 'price_unit':  160.00, 'tax_amount_currency':  36.92, 'state': 'reported'},
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

        # Approving properly change states & create moves & payments
        expense_sheets.action_approve_expense_sheets()
        self.assertRecordValues(expense_sheets, [
            {'state': 'approve', 'payment_state': 'not_paid'},
            {'state': 'approve', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(expense_sheets.expense_line_ids, [
            {'state': 'approved'},
            {'state': 'approved'},
            {'state': 'approved'},
            {'state': 'approved'},
        ])
        employee_partner_id = self.expense_user_employee.partner_id.id
        self.assertRecordValues(expense_sheets.account_move_ids.sorted(lambda move: (move.expense_sheet_id, move)), [
            {'amount_total':  1760.00, 'ref': 'Expense for John Smith', 'date': date(2021, 10, 31), 'partner_id': employee_partner_id, 'state': 'draft'},
            {'amount_total':   160.00, 'ref': 'PB 160 + 2*15% 2',       'date': date(2021, 10, 12), 'partner_id': False, 'state': 'draft'},
            {'amount_total':  1000.00, 'ref': 'PC 1000 + 15%',          'date': date(2021, 10, 11), 'partner_id': False, 'state': 'draft'},
        ])

        # Post a payment for 'company_account' (and its move(s)) and a vendor bill for 'own_account'
        expense_sheets.action_sheet_move_post()
        self.assertRecordValues(expense_sheets, [
            {'state': 'post', 'payment_state': 'not_paid',    'accounting_date': date(2021, 10, 10)},
            # Expense sheet paid by company don't use accounting date since they are already paid and posted directly
            {'state': 'done', 'payment_state': 'paid',        'accounting_date': False},
        ])
        self.assertRecordValues(expense_sheets.expense_line_ids, [
            {'payment_mode': 'own_account',     'state': 'approved'},
            {'payment_mode': 'own_account',     'state': 'approved'},  # As the payment is not done yet those are still in "approved"
            {'payment_mode': 'company_account', 'state': 'done'},
            {'payment_mode': 'company_account', 'state': 'done'},
        ])
        # One payment for the whole sheet if 'own_account'
        self.assertRecordValues(expense_sheet_by_employee.account_move_ids, [{
            'amount_total': 1760.00,
            'ref': 'Expense for John Smith',
            'date': date(2021, 10, 31),  # End of month since it is from a previous month computed by account.move
            'invoice_date': date(2021, 10, 10),
            'invoice_date_due': date(2021, 11, 9),  # The due date is the one set for the partner
            'partner_id': employee_partner_id,
            'state': 'posted',
        },
        ])
        # One payment per expense if 'company_account'
        self.assertRecordValues(expense_sheet_by_company.account_move_ids, [
            {'amount_total':   160.00, 'ref': 'PB 160 + 2*15% 2', 'date': date(2021, 10, 12), 'partner_id': False, 'state': 'posted'},
            {'amount_total':  1000.00, 'ref': 'PC 1000 + 15%',    'date': date(2021, 10, 11), 'partner_id': False, 'state': 'posted'},
        ])
        tax_account_id = self.company_data['default_account_tax_purchase'].id
        default_account_payable_id = self.company_data['default_account_payable'].id
        product_b_account_id = self.product_b.property_account_expense_id.id
        product_c_account_id = self.product_c.property_account_expense_id.id
        company_payment_account_id = self.outbound_payment_method_line.payment_account_id.id
        # One payment per expense
        self.assertRecordValues(expense_sheets.account_move_ids.line_ids.sorted(lambda line: (line.move_id.expense_sheet_id, line)), [
            # own_account expense sheet move
            # Invoice date should be the one set as accounting date in the expense sheet
            {'balance':  1391.30, 'account_id': self.expense_account.id,    'name': 'expense_employee: PA 2*800 + 15%',   'date': date(2021, 10, 31),           'invoice_date': date(2021, 10, 10)},
            {'balance':   123.08, 'account_id': product_b_account_id,       'name': 'expense_employee: PB 160 + 2*15%',   'date': date(2021, 10, 31),           'invoice_date': date(2021, 10, 10)},
            {'balance':   208.70, 'account_id': tax_account_id,             'name': '15%',                                'date': date(2021, 10, 31),           'invoice_date': date(2021, 10, 10)},
            {'balance':    18.46, 'account_id': tax_account_id,             'name': '15%',                                'date': date(2021, 10, 31),           'invoice_date': date(2021, 10, 10)},
            {'balance':    18.46, 'account_id': tax_account_id,             'name': '15% (Copy)',                         'date': date(2021, 10, 31),           'invoice_date': date(2021, 10, 10)},
            {'balance': -1760.00, 'account_id': default_account_payable_id, 'name': False,                                   'date': date(2021, 10, 31),           'invoice_date': date(2021, 10, 10)},

            # company_account expense 2 move
            {'balance':  123.08, 'account_id': product_b_account_id,        'name': 'expense_employee: PB 160 + 2*15% 2', 'date': date(2021, 10, 12),           'invoice_date': False},
            {'balance':   18.46, 'account_id': tax_account_id,              'name': '15%',                                'date': date(2021, 10, 12),           'invoice_date': False},
            {'balance':   18.46, 'account_id': tax_account_id,              'name': '15% (Copy)',                         'date': date(2021, 10, 12),           'invoice_date': False},
            {'balance': -160.00, 'account_id': company_payment_account_id,  'name': 'expense_employee: PB 160 + 2*15% 2', 'date': date(2021, 10, 12),           'invoice_date': False},

            # company_account expense 1 move
            {'balance':   869.57, 'account_id': product_c_account_id,       'name': 'expense_employee: PC 1000 + 15%',    'date': date(2021, 10, 11),           'invoice_date': False},
            {'balance':   130.43, 'account_id': tax_account_id,             'name': '15%',                                'date': date(2021, 10, 11),           'invoice_date': False},
            {'balance': -1000.00, 'account_id': company_payment_account_id, 'name': 'expense_employee: PC 1000 + 15%',    'date': date(2021, 10, 11),           'invoice_date': False},
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
        self.assertFalse(expense_sheet_by_employee.account_move_ids)

        with self.assertRaises(UserError, msg="For company-paid expenses report, deleting payments is an all-or-nothing situation"):
            expense_sheet_by_company.account_move_ids[:-1].origin_payment_id.unlink()
        expense_sheet_by_company.account_move_ids.origin_payment_id.unlink()
        self.assertFalse(expense_sheet_by_company.account_move_ids)

        self.assertRecordValues(expense_sheets.sorted('payment_mode'), [
            {'payment_mode': 'company_account', 'state': 'approve', 'payment_state': 'not_paid', 'account_move_ids': []},
            {'payment_mode': 'own_account',     'state': 'approve', 'payment_state': 'not_paid', 'account_move_ids': []},
        ])

        expense_sheet_by_employee.action_reset_expense_sheets()
        self.assertRecordValues(expense_sheet_by_employee, [{'state': 'draft', 'payment_state': 'not_paid', 'account_move_ids': []}])
        expense_sheet_by_employee.expense_line_ids.unlink()
        # Only possible if no expense linked to the account
        self.analytic_account_1.unlink()

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'accounting_date': '2021-01-01',
            'payment_method_line_id': self.outbound_payment_method_line.id,
            'expense_line_ids': [
                Command.create({
                    'name': 'Car Travel Expenses',
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'total_amount': 350.00,
                    'payment_mode': 'company_account',
                    'date': '2024-01-01',
                }),
                Command.create({
                    'name': 'Lunch expense',
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'total_amount': 90.00,
                    'payment_mode': 'company_account',
                    'date': '2024-01-12',
                }),
            ]
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        move_twelve_january, move_first_january = expense_sheet.account_move_ids

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
        self.assertEqual(expense_sheet.state, 'done', 'sheet should be marked as done')
        self.assertTrue(90 == move_twelve_january.amount_total == move_twelve_january.origin_payment_id.amount)
        self.assertTrue(350 == move_first_january.amount_total == move_first_january.origin_payment_id.amount)
        self.assertEqual(440, expense_sheet.total_amount)
        self.assertEqual(expense_sheet.payment_state, 'paid', 'payment_state should be paid')

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
        foreign_currency_1 = self.other_currency
        foreign_currency_2 = self.setup_other_currency('GBP', rounding=0.01, rates=([('2016-01-01', 1 / 1.52)]))
        foreign_currency_3 = self.setup_other_currency('CAD', rounding=0.01, rates=([('2016-01-01', 1 / 0.148431)]))
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
        expenses_sheet_currencies_mix.action_sheet_move_post()
        self.assertRecordValues(expenses_sheet_currencies_mix.account_move_ids.sorted('id'), [
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1000.00, 'currency_id': foreign_currency_1.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1520.00, 'currency_id': foreign_currency_2.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 2000.00, 'currency_id': foreign_currency_2.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed':  500.00, 'currency_id': foreign_currency_1.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 1520.00, 'currency_id': foreign_currency_2.id},
            {'amount_total_in_currency_signed': 1000.00, 'amount_total_signed': 3000.00, 'currency_id': foreign_currency_2.id},
        ])
        self.assertRecordValues(expenses_sheet_currencies_mix.account_move_ids.origin_payment_id.sorted('id'), [
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_1.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_1.id},
            {'amount': 1000.00, 'payment_type': 'outbound', 'currency_id': foreign_currency_2.id},
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
        expense_sheets_rounding.action_sheet_move_post()

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

    def test_computation_expense_report_date_based_most_recent_expense_today(self):
        """
            Test the accounting date if the most recent expense is today
            The accounting date should then be today
        """
        expense_sheet = self.create_expense_report({
            'name': 'Expense for John Smith',
            'expense_line_ids': [
                Command.create({
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_a.id,
                    'price_unit': 1000.00,
                    'date': '2022-01-25',
                }),
                Command.create({
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_a.id,
                    'price_unit': 200.00,
                    'date': '2022-01-20',
                })
            ],
        })
        expense_sheet.action_submit_sheet()
        with freeze_time(self.frozen_today):
            expense_sheet.action_approve_expense_sheets()
            expense_sheet.action_sheet_move_post()

        self.assertEqual(expense_sheet.accounting_date, fields.Date.from_string('2022-01-25'))

    def test_computation_expense_report_date_based_user_input(self):
        """
            Test the accounting date if the accounting date is from the form
            The accounting date should then not be changed
        """
        expense_sheet = self.create_expense_report({
            'name': 'Expense for John Smith',
            'accounting_date': '2024-03-10',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2022-01-25',
            })],
        })
        expense_sheet.action_submit_sheet()
        with freeze_time(self.frozen_today):
            expense_sheet.action_approve_expense_sheets()
            expense_sheet.action_sheet_move_post()

        self.assertEqual(expense_sheet.accounting_date, fields.Date.from_string('2024-03-10'))

    def test_computation_expense_report_date_with_most_recent_expense_within_month_early(self):
        """
            Test the accounting date if the most recent expense is within this month but earlier than today
            The accounting date should then be today
        """
        expense_sheet = self.create_expense_report({
            'name': 'Expense for John Smith',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2022-01-01',
            })],
        })

        expense_sheet.action_submit_sheet()

        with freeze_time(self.frozen_today):
            expense_sheet.action_approve_expense_sheets()
            expense_sheet.action_sheet_move_post()

        self.assertEqual(expense_sheet.accounting_date, fields.Date.from_string('2022-01-25'))

    def test_computation_expense_report_date_with_most_recent_expense_within_month_later(self):
        """
            Test the accounting date if the most recent expense is within this month but after today
            The accounting date should then be today
        """
        expense_sheet_2 = self.create_expense_report({
            'name': 'Expense for John Smith',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2022-01-29',
            })],
        })
        expense_sheet_2.action_submit_sheet()

        with freeze_time(self.frozen_today):
            expense_sheet_2.action_approve_expense_sheets()
            expense_sheet_2.action_sheet_move_post()

        self.assertEqual(expense_sheet_2.accounting_date, fields.Date.from_string('2022-01-25'))

    def test_computation_expense_report_date_with_most_recent_expense_last_month(self):
        """
            Test the accounting date if the most recent expense is before this month and there is no lock date
            The accounting date should then be the last day of the mst recent expense month
        """
        expense_sheet = self.create_expense_report({
            'name': 'Expense for John Smith',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2021-12-20',
            })],
        })
        expense_sheet.action_submit_sheet()

        with freeze_time(self.frozen_today):
            expense_sheet.action_approve_expense_sheets()
            expense_sheet.action_sheet_move_post()

        # no lock date so defaults to last day of month of the most recent expense
        self.assertEqual(expense_sheet.accounting_date, fields.Date.from_string('2021-12-31'))

        expense_sheet_2 = self.create_expense_report({
            'name': 'Expense for John Smith 2',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2022-01-25',
            })],
        })
        expense_sheet_2.action_submit_sheet()

        with freeze_time('2022-02-25'):
            expense_sheet_2.action_approve_expense_sheets()
            expense_sheet_2.action_sheet_move_post()

        self.assertEqual(expense_sheet_2.accounting_date, fields.Date.from_string('2022-01-31'))

    def test_computation_expense_report_date_with_most_recent_expense_last_month_with_lock_date(self):
        """
           Test the accounting date if the most recent expense is before this month and there is a lock date
           The accounting date should then be the min(max(of the last day of most recent expense month AND last day of month after lock date) AND today)
       """
        self.env.company.fiscalyear_lock_date = '2021-12-31'

        expense_sheet = self.create_expense_report({
            'name': 'Expense for John Smith',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2021-12-20',
            })],
        })
        expense_sheet.action_submit_sheet()

        with freeze_time(self.frozen_today):
            expense_sheet.action_approve_expense_sheets()
            expense_sheet.action_sheet_move_post()

        # today
        self.assertEqual(expense_sheet.accounting_date, fields.Date.from_string('2022-01-25'))

        expense_sheet_2 = self.create_expense_report({
            'name': 'Expense for John Smith 2',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2022-01-25',
            })],
        })
        expense_sheet_2.action_submit_sheet()

        with freeze_time("2022-02-25"):
            expense_sheet_2.action_approve_expense_sheets()
            expense_sheet_2.action_sheet_move_post()

        self.assertEqual(expense_sheet_2.accounting_date, fields.Date.from_string('2022-01-31'))

        # another lock date
        self.env.company.fiscalyear_lock_date = '2022-01-1'

        expense_sheet_3 = self.create_expense_report({
            'name': 'Expense for John Smith 3',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1400.00,
                'date': '2021-12-19',
            })],
        })
        expense_sheet_3.action_submit_sheet()

        with freeze_time(self.frozen_today):
            expense_sheet_3.action_approve_expense_sheets()
            expense_sheet_3.action_sheet_move_post()

        # today
        self.assertEqual(expense_sheet_3.accounting_date, fields.Date.from_string('2022-01-25'))

        expense_sheet_4 = self.create_expense_report({
            'name': 'Expense for John Smith 4',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1200.00,
                'date': '2022-01-19',
            })],
        })
        expense_sheet_4.action_submit_sheet()

        with freeze_time("2022-02-25"):
            expense_sheet_4.action_approve_expense_sheets()
            expense_sheet_4.action_sheet_move_post()

        self.assertEqual(expense_sheet_4.accounting_date, fields.Date.from_string('2022-02-25'))

    def test_accounting_date_reset_after_draft_reset(self):
        """
        Test that the accounting date is reset to False when we reset the sheet to draft
        """
        expense_sheet = self.create_expense_report({
            'name': 'Expense for John Smith',
            'expense_line_ids': [Command.create({
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'price_unit': 1000.00,
                'date': '2021-12-20',
            })],
        })
        expense_sheet.action_submit_sheet()
        self.assertEqual(expense_sheet.state, 'submit', "The expense sheet must be submitted")
        expense_sheet.action_approve_expense_sheets()
        self.assertEqual(expense_sheet.state, 'approve', "The expense sheet must be approved")
        expense_sheet.action_sheet_move_post()
        expense_sheet.action_reset_expense_sheets()
        self.assertEqual(expense_sheet.state, 'draft', "The expense sheet must be reset to draft")
        self.assertEqual(expense_sheet.accounting_date, False, "Accounting date must be reset when expense report is reset to draft")

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
        self.assertEqual(expense.tax_ids, product.supplier_taxes_id.filtered(lambda t: t.company_id == expense.company_id))
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
        expense_sheet.action_sheet_move_post()

        self.assertRecordValues(expense_sheet.account_move_ids.attachment_ids.sorted('name'), [
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
        expense_sheet.action_sheet_move_post()

        expense_move = expense_sheet.account_move_ids.filtered(lambda am: am.invoice_line_ids[0].ref == 'Company expense')
        expense_2_move = expense_sheet.account_move_ids.filtered(lambda am: am.invoice_line_ids[0].ref == 'Company expense 2')
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
        expense_sheet.action_sheet_move_post()
        self.assertRecordValues(expense_sheet.account_move_ids.origin_payment_id, [{'payment_method_line_id': new_payment_method_line.id}])

    @freeze_time('2024-01-01')
    def test_expense_vendor(self):
        """ This test will do a basic flow when a vendor is set on the expense """
        vendor_a = self.env['res.partner'].create({'name': 'Ruben'})
        vendor_b = self.env['res.partner'].create({'name': 'Flo'})
        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Sheet test',
            'employee_id': self.expense_employee.id,
            'expense_line_ids': [
                Command.create({
                    'name': 'Expense test',
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'payment_mode': 'company_account',
                    'date': '2024-01-02',
                    'total_amount': 100,
                    'tax_ids': [self.tax_purchase_a.id, self.tax_purchase_b.id],
                    'vendor_id': vendor_a.id,
                }),
                Command.create({
                    'name': 'Expense test 2',
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'payment_mode': 'company_account',
                    'date': '2024-01-01',
                    'total_amount': 100,
                    'tax_ids': [self.tax_purchase_a.id, self.tax_purchase_b.id],
                    'vendor_id': vendor_b.id,
                }),

            ],
        })
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        self.assertEqual(vendor_a.id, expense_sheet.account_move_ids[0].line_ids.partner_id.id)
        self.assertEqual(vendor_b.id, expense_sheet.account_move_ids[1].line_ids.partner_id.id)

    def test_payment_edit_fields(self):
        """ Test payment fields cannot be modified once linked with an expense
        """
        sheet = self.env['hr.expense.sheet'].create({
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': 'test sheet 2',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_c.id,
                    'total_amount': 10.0,
                    'payment_mode': 'company_account',
                    'employee_id': self.expense_employee.id
                }),
            ],
        })
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        payment = sheet.account_move_ids.origin_payment_id

        with self.assertRaises(UserError, msg="Cannot edit payment amount after linking to an expense"):
            payment.write({'amount': 500})

        payment.write({'is_sent': True})

    def test_corner_case_expense_reported_cannot_be_zero(self):
        """
        Test that the expenses are not submitted if the total amount is 0.0 nor able to be edited that way
        unless unlinking it from the expense sheet.
        """
        expense = self.create_expense({'total_amount': 0.0, 'total_amount_currency': 0.0})

        # CASE 1: FORBIDS Trying to submit an expense with a total_amount(_currency) of 0.0
        with self.assertRaises(UserError):
            expense.action_submit_expenses()

        # CASE 2: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense is linked to a sheet
        expense.total_amount_currency = 1000
        expense_sheet = expense._create_sheets_from_expense()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 3: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense sheet is approved
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 4: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the expense sheet is posted and the account move created
        expense_sheet.action_sheet_move_post()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 5: Should behave like CASE 2, the expense is still linked to a sheet after a reset to draft and shouldn't be updated
        expense_sheet.action_reset_expense_sheets()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0

        # CASE 6: ALLOWS Changing the total_amount(_currency) to 0.0 when the expense is unlinked from its sheet
        expense.sheet_id = False
        expense.write({'total_amount_currency': 0.0, 'total_amount': 0.0})

        # CASE 7: FORBIDS Setting the amounts to 0 while setting the sheet_id
        expense.write({'total_amount_currency': 1000.0, 'total_amount': 1000.0})
        with self.assertRaises(UserError):
            expense.write({'total_amount_currency': 0.0, 'sheet_id': expense_sheet.id})
        with self.assertRaises(UserError):
            expense.write({'total_amount': 0.0, 'sheet_id': expense_sheet.id})

        # CASE 8: ALLOWS Setting the amounts to 0 while unlinking the expense sheet
        expense.write({'total_amount_currency': 0.0, 'total_amount': 0.0, 'sheet_id': False})

    def test_corner_case_expense_prevent_empty_sheet_approval_actions(self):
        """
        Test that the expenses cannot not submitted, approved or posted if the sheet has no lines and that those lines cannot be removed
        """

        # CASE 1: FORBIDS Trying to submit an empty sheet
        expense_sheet = self.create_expense_report({'expense_line_ids': []})
        with self.assertRaises(UserError):
            expense_sheet.action_submit_sheet()

        # CASE 2: FORBIDS Trying to remove expense lines from a submitted expense sheet
        expense = self.create_expense()
        expense_sheet.expense_line_ids = expense.ids
        expense_sheet.action_submit_sheet()
        with self.assertRaises(UserError):
            expense_sheet.expense_line_ids = [Command.clear()]

        # CASE 3: FORBIDS Trying to remove expense lines from a submitted expense sheet
        expense_sheet.action_approve_expense_sheets()
        with self.assertRaises(UserError):
            expense_sheet.expense_line_ids = [Command.clear()]

        # CASE 4: FORBIDS Trying to remove expense lines from a posted expense sheet
        expense_sheet.action_sheet_move_post()
        with self.assertRaises(UserError):
            expense_sheet.expense_line_ids = [Command.clear()]

    def test_expense_sheet_attachments_sync(self):
        """
        Test that the hr.expense.sheet attachments stay in sync with the attachments associated with the expense lines
        Syncing should happen when:
        - When adding/removing expense_line_ids on a hr.expense.sheet <-> changing sheet_id on an expense
        - When deleting an expense that is associated with an hr.expense.sheet
        - When adding/removing an attachment of an expense that is associated with an hr.expense.sheet
        """
        def assert_attachments_are_synced(sheet, attachments_on_sheet, sheet_has_attachment):
            if sheet_has_attachment:
                self.assertTrue(bool(attachments_on_sheet), "Attachment that belongs to the hr.expense.sheet only was removed unexpectedly")
            self.assertSetEqual(
                set(sheet.expense_line_ids.attachment_ids.mapped('checksum')),
                set((sheet.attachment_ids - attachments_on_sheet).mapped('checksum')),
                "Attachments between expenses and their sheet is not in sync.",
            )

        for sheet_has_attachment in (False, True):
            expense_1, expense_2, expense_3 = self.env['hr.expense'].create([{
                'name': 'expense_1',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 1000,
            }, {
                'name': 'expense_2',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 999,
            }, {
                'name': 'expense_3',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_c.id,
                'total_amount': 998,
            }])
            self.env['ir.attachment'].create([{
                'name': "test_file_1.txt",
                'datas': base64.b64encode(b'content'),
                'res_id': expense_1.id,
                'res_model': 'hr.expense',
            }, {
                'name': "test_file_2.txt",
                'datas': base64.b64encode(b'other content'),
                'res_id': expense_2.id,
                'res_model': 'hr.expense',
            }, {
                'name': "test_file_3.txt",
                'datas': base64.b64encode(b'different content'),
                'res_id': expense_3.id,
                'res_model': 'hr.expense',
            }])

            sheet = self.env['hr.expense.sheet'].create({
                'company_id': self.env.company.id,
                'employee_id': self.expense_employee.id,
                'name': 'test sheet',
                'expense_line_ids': [Command.set([expense_1.id, expense_2.id, expense_3.id])],
            })

            sheet_attachment = self.env['ir.attachment'].create({
                'name': "test_file_4.txt",
                'datas': base64.b64encode(b'yet another different content'),
                'res_id': sheet.id,
                'res_model': 'hr.expense.sheet',
            }) if sheet_has_attachment else self.env['ir.attachment']

            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            expense_1.attachment_ids.unlink()
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            self.env['ir.attachment'].create({
                'name': "test_file_1.txt",
                'datas': base64.b64encode(b'content'),
                'res_id': expense_1.id,
                'res_model': 'hr.expense',
            })
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            expense_2.sheet_id = False
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            expense_2.sheet_id = sheet
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            sheet.expense_line_ids = [Command.set([expense_1.id, expense_3.id])]
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            expense_3.unlink()
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            sheet.attachment_ids.filtered(
                lambda att: att.checksum in sheet.expense_line_ids.attachment_ids.mapped('checksum')
            ).unlink()
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)

    def test_expense_sheet_with_employee_of_no_work_email(self):
        """
        Should raise a RedirectWarning when the selected employee in the sheet doesn't have a work email.
        """
        # Create two employees with no work email
        employee = self.env["hr.employee"].create([
            {
                'name': "Test Employee1"
            },
        ])
        # Create an expense with the above created employees
        expense = self.create_expense({'employee_id': employee.id})
        sheet = expense._create_sheets_from_expense()

        sheet.action_submit_sheet()
        with self.assertRaises(RedirectWarning):
            sheet.action_approve_expense_sheets()

    def test_create_report_name(self):
        """
            When an expense sheet is created from one or more expense, the report name is generated through the expense name or date.
            As the expense sheet is created directly from the hr.expense._get_default_expense_sheet_values method,
            we only need to test the method.
        """
        expense_with_date_1, expense_with_date_2, expense_without_date = self.env['hr.expense'].create([{
            'company_id': self.company_data['company'].id,
            'name': f'test expense {i}',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'date': '2021-01-01',
            'quantity': i + 1,
        } for i in range(3)])
        expense_without_date.date = False

        # CASE 1: only one expense with or without date -> expense name
        sheet_name = expense_with_date_1._get_default_expense_sheet_values()[0]['name']
        self.assertEqual(expense_with_date_1.name, sheet_name, "The report name should be the same as the expense name")
        sheet_name = expense_without_date._get_default_expense_sheet_values()[0]['name']
        self.assertEqual(expense_without_date.name, sheet_name, "The report name should be the same as the expense name")

        # CASE 2: two expenses with the same date -> expense date
        expenses = expense_with_date_1 | expense_with_date_2
        sheet_name = expenses._get_default_expense_sheet_values()[0]['name']
        self.assertEqual(format_date(self.env, expense_with_date_1.date), sheet_name, "The report name should be the same as the expense date")

        # CASE 3: two expenses with different dates -> date range
        expense_with_date_2.date = '2021-01-02'
        sheet_name = expenses._get_default_expense_sheet_values()[0]['name']
        self.assertEqual(
            f"{format_date(self.env, expense_with_date_1.date)} - {format_date(self.env, expense_with_date_2.date)}",
            sheet_name,
            "The report name should be the date range of the expenses",
        )

        # CASE 4: One or more expense doesn't have a date (single sheet) -> No fallback name
        expenses |= expense_without_date
        sheet_name = expenses._get_default_expense_sheet_values()[0]['name']
        self.assertFalse(
            sheet_name,
            "The report (with the empty expense date) name should be empty as a fallback when several reports are created",
        )
        expenses.date = False
        sheet_name = expenses._get_default_expense_sheet_values()[0]['name']
        self.assertFalse(sheet_name, "The report name should be empty as a fallback")

        # CASE 5: One or more expense doesn't have a date (multiple sheets) -> Fallback name
        expenses |= self.env['hr.expense'].create([{
            'company_id': self.company_data['company'].id,
            'name': f'test expense by company {i}',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'payment_mode': 'company_account',
            'date': '2021-01-01',
            'quantity': i + 1,
        } for i in range(3)])
        sheet_names = [sheet['name'] for sheet in expenses._get_default_expense_sheet_values()]
        self.assertSequenceEqual(
            ("New Expense Report, paid by employee", format_date(self.env, expenses[-1].date)),
            sheet_names,
            "The report name should be 'New Expense Report, paid by (employee|company)' as a fallback",
        )

    def test_foreign_currencies_total(self):
        Expense = self.env['hr.expense'].with_user(self.expense_user_employee)
        Expense.create([{
            'name': 'Company expense',
            'payment_mode': 'company_account',
            'total_amount_currency': 1000.00,
            'employee_id': self.expense_employee.id,
        },
        {
            'name': 'Company expense 2',
            'payment_mode': 'company_account',
            'currency_id': self.other_currency.id,
            'total_amount_currency': 1000.00,
            'total_amount': 2000.00,
            'employee_id': self.expense_employee.id,
        }])
        expense_state = Expense.get_expense_dashboard()
        self.assertEqual(expense_state['to_submit']['amount'], 3000.00)

    def test_update_expense_price_on_product_standard_price(self):
        """
        Tests that updating the standard price of a product will update all the un-submitted
        expenses using that product as a category.
        """
        product = self.env['product.product'].create({
            'name': 'Product',
            'standard_price': 100.0,
        })
        sheet_no_update, sheet_update = sheets = self.env['hr.expense.sheet'].create([{
            'company_id': self.env.company.id,
            'employee_id': self.expense_employee.id,
            'name': name,
            'expense_line_ids': [
                Command.create({
                    'name': name,
                    'date': '2016-01-01',
                    'product_id': product.id,
                    'total_amount': 100.0,
                    'employee_id': self.expense_employee.id
                }),
            ],
        } for name in ('test sheet no update', 'test sheet update')])

        sheet_no_update.action_submit_sheet()  # No update when sheet is submitted
        product.standard_price = 100.0

        self.assertRecordValues(sheets.expense_line_ids.sorted('name'), [
            {'name': 'test sheet no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
            {'name':    'test sheet update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
        ])

        self.assertRecordValues(sheets.expense_line_ids.sorted('name'), [
            {'name': 'test sheet no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
            {'name':    'test sheet update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
        ])
        product.standard_price = 50.0
        self.assertRecordValues(sheets.expense_line_ids.sorted('name'), [
            {'name': 'test sheet no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
            {'name':    'test sheet update', 'price_unit':  50.0, 'quantity': 1, 'total_amount':  50.0},  # price_unit is updated
        ])
        sheet_update.expense_line_ids.quantity = 5
        self.assertRecordValues(sheets.expense_line_ids.sorted('name'), [
            {'name': 'test sheet no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
            {'name':    'test sheet update', 'price_unit':  50.0, 'quantity': 5, 'total_amount': 250.0},  # quantity & total are updated
        ])
        product.standard_price = 0.0
        self.assertRecordValues(sheets.expense_line_ids.sorted('name'), [
            {'name': 'test sheet no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
            {'name':    'test sheet update', 'price_unit': 250.0, 'quantity': 1, 'total_amount': 250.0},  # quantity & price_unit only are updated
        ])

        sheet_update.action_submit_sheet()  # This sheet should not be updated any more
        product.standard_price = 300.0
        self.assertRecordValues(sheets.expense_line_ids.sorted('name'), [
            {'name': 'test sheet no update', 'price_unit': 100.0, 'quantity': 1, 'total_amount': 100.0},
            {'name':    'test sheet update', 'price_unit': 250.0, 'quantity': 1, 'total_amount': 250.0},  # no update
        ])

    def test_expense_standard_price_update_warning(self):
        self.expense_cat_A = self.env['product.product'].create({
            'name': 'Category A',
            'default_code': 'CA',
            'standard_price': 0.0,
        })
        self.expense_cat_B = self.env['product.product'].create({
            'name': 'Category B',
            'default_code': 'CB',
            'standard_price': 0.0,
        })
        self.expense_cat_C = self.env['product.product'].create({
            'name': 'Category C',
            'default_code': 'CC',
            'standard_price': 0.0,
        })
        self.expense_1 = self.env['hr.expense'].create({
            'employee_id': self.expense_employee.id,
            'name': 'Expense 1',
            'product_id': self.expense_cat_A.id,
            'total_amount': 1,
        })
        self.expense_2 = self.env['hr.expense'].create({
            'employee_id': self.expense_employee.id,
            'name': 'Expense 2',
            'product_id': self.expense_cat_B.id,
            'total_amount': 5,
        })

        # At first, there is no warning message on the categories because their prices are 0
        self.assertFalse(self.expense_cat_A.standard_price_update_warning)
        self.assertFalse(self.expense_cat_B.standard_price_update_warning)
        self.assertFalse(self.expense_cat_C.standard_price_update_warning)

        # When modifying the price of the first category, a message should appear as a an expense will be modified.
        with Form(self.expense_cat_A, view="hr_expense.product_product_expense_form_view") as form:
            form.standard_price = 5
            self.assertTrue(form.standard_price_update_warning)

        # When modifying the price of the second category, no message should appear as the price of the linked
        # expense is the price of the category that is going to be saved.
        with Form(self.expense_cat_B, view="hr_expense.product_product_expense_form_view") as form:
            form.standard_price = 5
            self.assertFalse(form.standard_price_update_warning)

        # When modifying the price of the thirs category, no message should appear as no expense is linked to it.
        with Form(self.expense_cat_C, view="hr_expense.product_product_expense_form_view") as form:
            form.standard_price = 5
            self.assertFalse(form.standard_price_update_warning)

    def test_compute_standard_price_update_warning_product_with_and_without_expense(self):
        self.product_expensed = self.env['product.product'].create({
            'name': 'Category A',
            'default_code': 'CA',
            'standard_price': 0.0,
        })
        self.product_not_expensed = self.env['product.product'].create({
            'name': 'Category B',
            'default_code': 'CB',
            'standard_price': 0.0,
        })
        self.expense_1 = self.env['hr.expense'].create({
            'employee_id': self.expense_employee.id,
            'name': 'Expense 1',
            'product_id': self.product_expensed.id,
            'total_amount': 1,
        })

        (self.product_expensed | self.product_not_expensed)._compute_standard_price_update_warning()

    def test_expense_sheet_multi_company(self):
        self.expense_employee.company_id = self.company_data_2['company']

        # The expense employee is able to a create an expense sheet for company_2.
        # product_a needs a standard_price in company_2
        self.product_a.with_context(allowed_company_ids=self.company_data_2['company'].ids).standard_price = 100

        expense_sheet_approve = self.env['hr.expense.sheet'] \
            .with_user(self.expense_user_employee) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            .create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data_2['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [Command.create({
                # Expense without foreign currency but analytic account.
                'name': 'expense_1',
                'date': '2016-01-01',
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'employee_id': self.expense_employee.id,
            })],
        })
        expense_sheet_refuse = self.env['hr.expense.sheet'] \
            .with_user(self.expense_user_employee) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            .create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data_2['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [Command.create({
                # Expense without foreign currency but analytic account.
                'name': 'expense_1',
                'date': '2016-01-01',
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'employee_id': self.expense_employee.id,
            })],
        })
        expenses = expense_sheet_approve | expense_sheet_refuse
        self.assertRecordValues(expenses, [
            {'company_id': self.company_data_2['company'].id},
            {'company_id': self.company_data_2['company'].id},
        ])

        # The expense employee is able to submit the expense sheet.
        expenses.with_user(self.expense_user_employee).action_submit_sheet()

        # An expense manager is not able to approve nor refuse without access to company_2.
        with self.assertRaises(UserError):
            expense_sheet_approve \
                .with_user(self.expense_user_manager) \
                .with_context(allowed_company_ids=self.company_data['company'].ids) \
                .action_approve_expense_sheets()

        with self.assertRaises(UserError):
            expense_sheet_refuse \
                .with_user(self.expense_user_manager) \
                .with_context(allowed_company_ids=self.company_data['company'].ids) \
                ._do_refuse('failed')

        # An expense manager is able to approve/refuse with access to company_2.
        expense_sheet_approve \
            .with_user(self.expense_user_manager) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            .action_approve_expense_sheets()
        expense_sheet_refuse \
            .with_user(self.expense_user_manager) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            ._do_refuse('failed')

        # An expense manager having accounting access rights is not able to post the journal entry without access
        # to company_2.
        with self.assertRaises(UserError):
            (
                expense_sheet_approve
                .with_user(self.env.user)
                .with_context(allowed_company_ids=self.company_data['company'].ids)
                .action_sheet_move_post()
             )

        # An expense manager having accounting access rights is able to post the journal entry with access to
        # company_2.
        (
            expense_sheet_approve
                .with_user(self.env.user)
                .with_context(allowed_company_ids=self.company_data_2['company'].ids)
                .action_sheet_move_post()
        )

    def test_tax_is_used_when_in_transactions(self):
        ''' Ensures that a tax is set to used when it is part of some transactions '''

        # Account.move is one type of transaction
        tax_expense = self.env['account.tax'].create({
            'name': 'test_is_used_expenses',
            'amount': '100',
            'include_base_amount': True,
        })

        self.env['hr.expense'].create({
            'name': 'Test Tax Used',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount_currency': 350.00,
            'tax_ids': [Command.set(tax_expense.ids)]
        })
        tax_expense.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_expense.is_used)

    def test_expense_by_company_with_caba_tax(self):
        """When using cash basis tax in an expense paid by the company, the transition account should not be used."""

        caba_tag = self.env['account.account.tag'].create({
            'name': 'Cash Basis Tag Final Account',
            'applicability': 'taxes',
        })
        caba_transition_account = self.env['account.account'].create({
            'name': 'Cash Basis Tax Transition Account',
            'account_type': 'asset_current',
            'code': '131001',
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

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Company Cash Basis Expense Report',
            'employee_id': self.expense_employee.id,
            'payment_mode': 'company_account',
            'approval_state': 'approve',
            'expense_line_ids': [Command.create({
                'name': 'Company Cash Basis Expense',
                'product_id': self.product_c.id,
                'payment_mode': 'company_account',
                'total_amount': 20.0,
                'employee_id': self.expense_employee.id,
                'tax_ids': [Command.set(caba_tax.ids)],
            })]
        })
        expense_sheet.action_sheet_move_post()
        moves = expense_sheet.account_move_ids
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

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'accounting_date': '2021-01-01',
            'expense_line_ids': [Command.create({
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'total_amount': 350.00,
                'payment_mode': 'company_account',
            })]
        })

        expense_sheet.action_submit_sheet()
        with self.assertRaises(ValidationError, msg="One or more lines require a 100% analytic distribution."):
            expense_sheet.with_context(validate_analytic=True).action_approve_expense_sheets()

        expense_sheet.expense_line_ids.analytic_distribution = {self.analytic_account_1.id: 100.00}
        expense_sheet.with_context(validate_analytic=True).action_approve_expense_sheets()

    def test_expense_no_stealing_from_employees(self):
        """
        Test to check that the company doesn't steal their employee when the commercial_partner_id of the employee partner
        is the company
        """
        self.expense_employee.user_partner_id.parent_id = self.env.company.partner_id
        self.assertEqual(self.env.company.partner_id, self.expense_employee.user_partner_id.commercial_partner_id)

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Company Cash Basis Expense Report',
            'employee_id': self.expense_employee.id,
            'payment_mode': 'own_account',
            'state': 'approve',
            'expense_line_ids': [Command.create({
                'name': 'Company Cash Basis Expense',
                'product_id': self.product_c.id,
                'payment_mode': 'own_account',
                'total_amount': 20.0,
                'employee_id': self.expense_employee.id,
            })]
        })
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()
        move = expense_sheet.account_move_ids

        self.assertNotEqual(move.commercial_partner_id, self.env.company.partner_id)
        self.assertEqual(move.partner_id, self.expense_employee.user_partner_id)
        self.assertEqual(move.commercial_partner_id, self.expense_employee.user_partner_id)

    def test_expense_sheet_with_line_ids(self):
        """
        Test to create an expense sheet with no account date and having multiple expenses
        in which one of the expense doesn't have date to get the account date from the max date of expenses.
        """
        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'payment_method_line_id': self.outbound_payment_method_line.id,
            'expense_line_ids': [
                Command.create({
                    'name': 'Car Travel Expenses',
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'total_amount': 350.00,
                    'date': False,
                }),
                Command.create({
                    'name': 'Lunch expense',
                    'employee_id': self.expense_employee.id,
                    'product_id': self.product_c.id,
                    'total_amount': 90.00,
                    'date': '2024-04-30',
                }),
            ]
        })
        # Validate the values before submitting and approving
        self.assertRecordValues(expense_sheet, [
            {'total_amount': 440.00, 'accounting_date': False, 'state': 'draft', 'employee_id': self.expense_employee.id}
        ])
        self.assertRecordValues(expense_sheet.expense_line_ids, [
            {'name': 'Car Travel Expenses', 'total_amount': 350.00, 'date': False},
            {'name': 'Lunch expense', 'total_amount': 90.00, 'date': date(2024, 4, 30)},
        ])
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        # Validate the record values after submitting and approving
        self.assertRecordValues(expense_sheet, [
            {'total_amount': 440.00, 'accounting_date': date(2024, 4, 30), 'state': 'post', 'employee_id': self.expense_employee.id}
        ])
        self.assertRecordValues(expense_sheet.expense_line_ids, [
            {'name': 'Car Travel Expenses', 'total_amount': 350.00, 'date': False},
            {'name': 'Lunch expense', 'total_amount': 90.00, 'date': date(2024, 4, 30)},
        ])

        # Reset to draft to make the accounting_date to False and then recompute it
        expense_sheet.action_reset_expense_sheets()

        # Validate the accounting_date value to be false
        self.assertFalse(expense_sheet.accounting_date)

        # Update one of the expense sheet line date
        expense_sheet.expense_line_ids[1].write({'date': '2024-05-30'})

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        # Validate the acction_date value after subitting and approving
        self.assertTrue(expense_sheet.accounting_date, date(2024, 5, 30))

    def test_expense_bank_account_of_employee_on_entry_and_register_payment(self):
        """
        Test that the bank account defined on the employee form is correctly set on the entry and on the register payment
        when having multiple bank accounts defined on the partner
        """

        self.partner_bank_account_1 = self.env['res.partner.bank'].create({
            'acc_number': "987654321",
            'partner_id': self.expense_employee.user_partner_id.id,
            'acc_type': 'bank',
        })
        self.partner_bank_account_2 = self.env['res.partner.bank'].create({
            'acc_number': "123456789",
            'partner_id': self.expense_employee.user_partner_id.id,
            'acc_type': 'bank',
        })
        # Set the second bank account for the employee
        self.expense_employee.bank_account_id = self.partner_bank_account_2

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'payment_mode': 'own_account',
            'state': 'approve',
            'expense_line_ids': [Command.create({
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'payment_mode': 'own_account',
                'total_amount': 350.00,
            })]
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        move_bank_acc = expense_sheet.account_move_ids.partner_bank_id
        self.assertEqual(move_bank_acc, self.partner_bank_account_2)
        action_data = expense_sheet.action_register_payment()
        with Form(self.env['account.payment.register'].with_context(action_data['context'])) as pay_form:
            self.assertEqual(pay_form.partner_bank_id, self.partner_bank_account_2)

    def test_expense_set_total_amount_to_0(self):
        """Checks that amount fields are correctly updating when setting total_amount to 0"""
        expense = self.env['hr.expense'].create({
            'name': 'Expense with amount',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount_currency': 100.0,
            'tax_ids': self.tax_purchase_a.ids,
        })
        expense.total_amount_currency = 0.0
        self.assertTrue(expense.currency_id.is_zero(expense.tax_amount))
        self.assertTrue(expense.company_currency_id.is_zero(expense.total_amount))

    def test_expense_set_quantity_to_0(self):
        """Checks that amount fields except for unit_amount are correctly updating when setting quantity to 0"""
        expense = self.env['hr.expense'].create({
            'name': 'Expense with amount',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_b.id,
            'quantity': 10
        })
        expense.quantity = 0
        self.assertTrue(expense.currency_id.is_zero(expense.total_amount_currency))
        self.assertEqual(expense.company_currency_id.compare_amounts(expense.price_unit, self.product_b.standard_price), 0)

    def test_move_creation_with_quantity(self):
        expense_sheet = self.create_expense_report({
            'name': 'Expense for John Smith',
            'expense_line_ids': [Command.create({
                'name': 'Test expense line',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'quantity': 5,
                'payment_mode': 'company_account',
                'company_id': self.company_data['company'].id,
                'tax_ids': False,
            })],
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()
        self.assertRecordValues(expense_sheet.account_move_ids.line_ids, [
            {'balance': 4000.0, 'name': 'expense_employee: Test expense line', 'quantity': 5},
            {'balance': -4000.0, 'name': 'expense_employee: Test expense line', 'quantity': 1},
        ])
