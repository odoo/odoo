from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestProjectProjectTemplate(TransactionCase):
    def test_project_created_from_template_to_have_analytic_account(self):
        template_project_timesheet, template_project_no_timesheet = self.env['project.project.template'].create([
            {
                "name": "Template Project Timesheet",
                "allow_timesheets": True,
            },
            {
                "name": "Template Project No Timesheet",
                "allow_timesheets": False,
            },
        ])

        new_project_1 = template_project_timesheet.action_create_from_template()
        self.assertTrue(new_project_1.account_id, "A project created from template allowing timesheet should have an analytic account")
        new_project_2 = template_project_no_timesheet.action_create_from_template()
        self.assertFalse(new_project_2.account_id, "A project created from template disabling timesheet should not have an analytic account")
