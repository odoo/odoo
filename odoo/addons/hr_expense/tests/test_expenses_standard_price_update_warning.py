# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestExpenseStandardPriceUpdateWarning(TestExpenseCommon):
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
