# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


class TestAnalyticLine(TestCommonTimesheet):
    def test_check_timesheet_unit_amount(self):
        AccountAnalyticLine = self.env['account.analytic.line'].with_context(default_name='/')
        timesheet, analytic_line = AccountAnalyticLine.create([
            {
                'project_id': self.project_customer.id,
                'employee_id': self.empl_employee.id,
                'unit_amount': 1,
            },
            {
                'account_id': self.project_customer.account_id.id,
                'unit_amount': 1000000,
            },
        ])
        self.assertTrue(timesheet.is_timesheet, "The analytic line created should be a timesheet.")
        for value in (1000000, -1000000):
            with self.assertRaisesRegex(UserError, "You can't encode numbers with more than six digits."):
                AccountAnalyticLine.create({
                    'project_id': self.project_customer.id,
                    'employee_id': self.empl_employee.id,
                    'unit_amount': value,
                })
            with self.assertRaisesRegex(UserError, "You can't encode numbers with more than six digits."):
                timesheet.unit_amount = value

        self.assertFalse(analytic_line.is_timesheet, "The analytic line created should not be a timesheet since no project is set.")
        self.assertEqual(analytic_line.unit_amount, 1000000, "The user can enter a number with more than 6 digits for the analytic line which is not a timesheet.")
        analytic_line.unit_amount = 1000005
        self.assertEqual(analytic_line.unit_amount, 1000005, "The user can always alter the analytic to put the number he wants since it is not a timesheet.")
