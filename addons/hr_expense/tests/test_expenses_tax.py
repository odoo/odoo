# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestExpensesTax(TestExpenseCommon):
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
        expense_sheet.action_sheet_move_create()
        moves = expense_sheet.account_move_ids
        tax_lines = moves.line_ids.filtered(lambda line: line.tax_line_id == caba_tax)
        self.assertNotEqual(tax_lines.account_id, caba_transition_account, "The tax should not be on the transition account")
        self.assertEqual(tax_lines.tax_tag_ids, caba_tag, "The tax should still retrieve its tags")
