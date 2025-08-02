# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, HttpCase

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('post_install', '-at_install')
class TestExpensesTour(TestExpenseCommon, HttpCase):
    def test_tour_expenses(self):
        self.start_tour("/odoo", "hr_expense_test_tour", login="admin")

    def test_tour_expense_category(self):
        self.expense_user_manager.group_ids |= self.env.ref("product.group_product_manager")
        company = self.expense_user_manager.company_id

        expense_cat_A = self.env['product.product'].create({
            'can_be_expensed': True,
            'company_id': company.id,
            'default_code': 'CA',
            'name': 'Category A',
            'supplier_taxes_id': [],
            'standard_price': 0.0,
            'type': 'service',
        })
        expense_cat_B = self.env['product.product'].create({
            'can_be_expensed': True,
            'company_id': company.id,
            'default_code': 'CB',
            'name': 'Category B',
            'supplier_taxes_id': [],
            'standard_price': 0.0,
            'type': 'service',
        })
        expense_cat_C = self.env['product.product'].create({
            'default_code': 'CC',
            'company_id': company.id,
            'can_be_expensed': True,
            'name': 'Category C',
            'supplier_taxes_id': [],
            'standard_price': 0.0,
            'type': 'service',
        })
        self.create_expenses([
            {
                'company_id': company.id,
                'name': 'Expense 1',
                'product_id': expense_cat_A.id,
                'total_amount': 1,
            },
            {
                'company_id': company.id,
                'name': 'Expense 2',
                'product_id': expense_cat_B.id,
                'total_amount': 5,
            },
        ])

        self.env.flush_all()
        self.start_tour("/odoo", "change_expense_category_price_tour", login=self.expense_user_manager.login)

        self.assertEqual(
            expense_cat_A.standard_price,
            2.0,
            "The price of Category A should be updated to 2.0",
        )
        self.assertEqual(
            expense_cat_B.standard_price,
            6.0,
            "The price of Category B should be updated to 6.0",
        )
        self.assertEqual(
            expense_cat_C.standard_price,
            3.0,
            "The price of Category C should be updated to 3.0",
        )
