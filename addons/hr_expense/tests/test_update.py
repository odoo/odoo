# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.test_update import TestUpdateEmployeesCommon


class TestUpdateExpense(TestUpdateEmployeesCommon):

    def test_employee_with_expense_is_light_user(self):
        employee = self.env['hr.employee'].create({'name': 'Employee'})
        before = self._count()
        self.env['hr.expense'].create({'name': 'Expense', 'employee_id': employee.id, 'total_amount_currency': 10})
        self.assertEqual(self._count(), before + 1)
