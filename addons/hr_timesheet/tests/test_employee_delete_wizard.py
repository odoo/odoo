# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr.tests.common import TestHrCommon


class TestEmployeeDeleteWizard(TestHrCommon):
    def setUp(self):
        super().setUp()

    def test_delete_wizard_single_employee_with_timesheet(self):
        """ Test the deletion wizard in the case of a single employee """
        employee_A = self.env['hr.employee'].create([
            {
                'name': 'Employee A',
                'user_id': False,
                'work_email': 'employee_A@example.com',
            }
        ])

        delete_wizard = self.env['hr.employee.delete.wizard'].create({
            'employee_ids': [employee_A.id],
        })

        returned_action_Record = delete_wizard.action_archive()

        self.assertEqual(returned_action_Record['context']['active_ids'], [employee_A.id], "Employee should have been selected")
        self.assertEqual(returned_action_Record['context']['employee_termination'], True, "Employee Termination should have been set")
