from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestExpensesTax(TestExpenseCommon):

    def test_expense_by_company_with_caba_tax(self):
        """When using cash basis tax in an expense paid by the company, the transition account should not be used."""

        caba_account_type = self.env['account.account.type'].create({
            'name': 'Cash Basis',
            'type': 'other',
            'internal_group': 'asset',
        })
        caba_transition_account = self.env['account.account'].create({
            'name': 'Cash Basis Tax Transition Account',
            'user_type_id': caba_account_type.id,
            'code': '131001',
        })
        caba_tax = self.env['account.tax'].create({
            'name': 'Cash Basis Tax',
            'tax_exigibility': 'on_payment',
            'amount': 15,
            'cash_basis_transition_account_id': caba_transition_account.id,
        })

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Company Cash Basis Expense Report',
            'employee_id': self.expense_employee.id,
            'payment_mode': 'company_account',
            'state': 'approve',
            'expense_line_ids': [Command.create({
                'name': 'Company Cash Basis Expense',
                'product_id': self.product_b.id,
                'payment_mode': 'company_account',
                'unit_amount': 20.0,
                'employee_id': self.expense_employee.id,
                'tax_ids': [Command.set(caba_tax.ids)],
            })]
        })

        moves = expense_sheet.action_sheet_move_create()
        tax_lines = moves[expense_sheet.id].line_ids.filtered(lambda line: line.tax_line_id == caba_tax)
        self.assertNotEqual(tax_lines.account_id, caba_transition_account, "The tax should not be on the transition account")
