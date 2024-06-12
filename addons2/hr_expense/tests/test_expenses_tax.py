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
