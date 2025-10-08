# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, HttpCase
from odoo.addons.hr.tests.test_utils import get_admin_employee


@tagged('post_install', '-at_install')
class TestExpensesTour(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_employee = get_admin_employee(cls.env)

    def test_tour_expenses(self):
        self.start_tour("/odoo", "hr_expense_test_tour", login="admin")
