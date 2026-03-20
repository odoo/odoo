# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, HttpCase
from odoo.addons.hr.tests.test_utils import get_admin_employee

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('post_install', '-at_install')
class TestExpensesTour(TestExpenseCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_employee = get_admin_employee(cls.env(user=cls.env.ref('base.user_admin')))

    def test_tour_expenses(self):
        self.start_tour("/odoo", "hr_expense_test_tour", login="admin")

    def test_tour_expense_category(self):
        self.expense_user_manager.group_ids |= self.env.ref("product.group_product_manager")

        self.create_expenses([
            {
                'name': 'Expense 1',
                'product_id': self.product_a.id,
            },
            {
                'name': 'Expense 2',
                'product_id': self.product_b.id,
            },
        ])

        self.env.flush_all()
        self.start_tour("/odoo", "change_expense_category_price_tour", login=self.expense_user_manager.login)

        self.assertEqual(
            self.product_a.standard_price,
            2.0,
            "The price of Category A should be updated to 2.0",
        )
        self.assertEqual(
            self.product_b.standard_price,
            6.0,
            "The price of Category B should be updated to 6.0",
        )
        self.assertEqual(
            self.product_c.standard_price,
            3.0,
            "The price of Category C should be updated to 3.0",
        )
