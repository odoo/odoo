from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged, HttpCase
from odoo.tools import mute_logger


@tagged('-at_install', 'post_install')
class TestUi(TestExpenseCommon, HttpCase):
    browser_size = "1920,1080"

    def test_expense_manager_can_always_set_employee(self):
        """Test that users with access rights to `hr.expense` can set the employee on them
        by using the usual form view, even if they do not have access rights to `hr.employee`
        """
        employee_1 = self.expense_employee
        employee_2 = self.env['hr.employee'].sudo().create({'name': 'employee2'})
        expense = self.env['hr.expense'].create({
            'name': 'expense_for_tour_0',
            'employee_id': employee_2.id,
            'product_id': self.product_c.id,
            'total_amount': 1,
        })
        self.start_tour('/odoo', 'create_expense_no_employee_access_tour', login=self.expense_user_manager.login)
        self.assertEqual(expense.employee_id.id, employee_1.id, "Employee should have been changed by tour")

    def test_no_zero_amount_expense_in_expense(self):
        """
            The test ensures that attempting to submit an expense with a zero amount fails as expected
            and that a valid amount can be set subsequently.
        """
        expense = self.create_expenses({'name': 'expense_for_tour'})
        with mute_logger("odoo.http"):
            self.start_tour('/odoo', 'do_not_create_zero_amount_expense', login=self.expense_user_manager.login)
        self.assertEqual(expense.total_amount_currency, 10.0, "Expense amount should have been set by tour")
