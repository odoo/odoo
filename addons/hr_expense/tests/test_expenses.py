# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestAccountEntry(TestExpenseCommon):
    """
    Check journal entries when the expense product is having tax which is tax included.
    """

    def setUp(self):
        super(TestAccountEntry, self).setUp()

        self.setUpAdditionalAccounts()

        self.product_expense = self.env['product.product'].create({
            'name': "Delivered at cost",
            'standard_price': 700,
            'list_price': 700,
            'type': 'consu',
            'supplier_taxes_id': [(6, 0, [self.tax.id])],
            'default_code': 'CONSU-DELI-COST',
            'taxes_id': False,
            'property_account_expense_id': self.account_expense.id,
        })

    def test_account_entry(self):
        """ Checking accounting move entries and analytic entries when submitting expense """
        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.employee.id,
        })
        expense_line = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses',
            'employee_id': self.employee.id,
            'product_id': self.product_expense.id,
            'unit_amount': 700.00,
            'tax_ids': [(6, 0, [self.tax.id])],
            'sheet_id': expense.id,
            'analytic_account_id': self.analytic_account.id,
        })
        expense_line._onchange_product_id()
        # Submitted to Manager
        self.assertEquals(expense.state, 'submit', 'Expense is not in Reported state')
        # Approve
        expense.approve_expense_sheets()
        self.assertEquals(expense.state, 'approve', 'Expense is not in Approved state')
        # Create Expense Entries
        expense.action_sheet_move_create()
        self.assertEquals(expense.state, 'post', 'Expense is not in Waiting Payment state')
        self.assertTrue(expense.account_move_id.id, 'Expense Journal Entry is not created')

        # [(line.debit, line.credit, line.tax_line_id.id) for line in self.expense.expense_line_ids.account_move_id.line_ids]
        # should git this result [(0.0, 700.0, False), (63.64, 0.0, 179), (636.36, 0.0, False)]
        for line in expense.account_move_id.line_ids:
            if line.credit:
                self.assertAlmostEquals(line.credit, 700.00)
                self.assertEquals(len(line.analytic_line_ids), 0, "The credit move line should not have analytic lines")
                self.assertFalse(line.product_id, "Product of credit move line should be false")
            else:
                if not line.tax_line_id == self.tax:
                    self.assertAlmostEquals(line.debit, 636.36)
                    self.assertEquals(len(line.analytic_line_ids), 1, "The debit move line should have 1 analytic lines")
                    self.assertEquals(line.product_id, self.product_expense, "Product of debit move line should be the one from the expense")
                else:
                    self.assertAlmostEquals(line.debit, 63.64)
                    self.assertEquals(len(line.analytic_line_ids), 0, "The tax move line should not have analytic lines")
                    self.assertFalse(line.product_id, "Product of tax move line should be false")

        self.assertEquals(self.analytic_account.line_ids, expense.account_move_id.mapped('line_ids.analytic_line_ids'))
        self.assertEquals(len(self.analytic_account.line_ids), 1, "Analytic Account should have only one line")
        self.assertAlmostEquals(self.analytic_account.line_ids[0].amount, -636.36, "Amount on the only AAL is wrong")
        self.assertEquals(self.analytic_account.line_ids[0].product_id, self.product_expense, "Product of AAL should be the one from the expense")
