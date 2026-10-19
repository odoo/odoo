from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


@tagged('post_install', '-at_install')
class TestEmployeeDeleteWizard(TestCommonTimesheet):
    """ Deleting an employee goes through a wizard which refuses the deletion as long as
        the employee has timesheets, and offers to archive the employee instead.
    """

    def _open_wizard(self, employees, user):
        action = employees.with_user(user).action_unlink_wizard()
        self.assertEqual(action['res_model'], 'hr.employee.delete.wizard')
        return self.env['hr.employee.delete.wizard'].browse(action['res_id'])

    def test_delete_employee_without_timesheet(self):
        wizard = self._open_wizard(self.empl_employee2, self.user_manager)
        self.assertFalse(wizard.has_timesheet)
        self.assertTrue(wizard.has_active_employee)

        wizard.action_confirm_delete()
        self.assertFalse(self.empl_employee2.exists(), "The employee should have been deleted")

    def test_archive_employee_with_timesheet(self):
        wizard = self._open_wizard(self.empl_employee, self.user_manager)
        self.assertTrue(wizard.has_timesheet)
        self.assertTrue(wizard.has_active_employee)

        wizard.action_archive()
        self.assertFalse(self.empl_employee.active, "The employee should have been archived")
        self.assertTrue(self.timesheet.exists(), "The timesheets of the employee should be kept")

    def test_delete_archived_employee_with_timesheet_as_approver(self):
        """ Once the employee is archived, the only way out is to delete their timesheets,
            so the wizard gives the approver a way to reach them.
        """
        self.empl_employee.action_archive()
        wizard = self._open_wizard(self.empl_employee, self.user_manager)
        self.assertTrue(wizard.has_timesheet)
        self.assertFalse(wizard.has_active_employee)

        action = wizard.action_open_timesheets()
        self.assertEqual(
            self.env['account.analytic.line'].search(action['domain']), self.timesheet,
            "The action should list the timesheets of the archived employee")

    def test_delete_archived_employee_with_timesheet_without_approval_rights(self):
        user_hr = new_test_user(
            self.env, 'user_hr',
            groups='hr.group_hr_manager,hr_timesheet.group_hr_timesheet_user',
        )
        self.empl_employee.action_archive()
        with self.assertRaises(UserError):
            self.empl_employee.with_user(user_hr).action_unlink_wizard()

    def test_delete_employees_of_which_only_one_has_timesheets(self):
        employees = self.empl_employee | self.empl_employee2
        wizard = self._open_wizard(employees, self.user_manager)
        self.assertTrue(wizard.has_timesheet, "One of the employees has a timesheet")

        wizard.action_archive()
        self.assertFalse(employees.filtered('active'), "Both employees should have been archived")
