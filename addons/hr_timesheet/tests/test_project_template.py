from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestProjectProjectTemplate(TransactionCase):

    def test_template_created_not_having_analytic_account(self):
        template_project, normal_project = self.env["project.project"].create(
            [
                {
                    "name": "Template Project",
                    "is_template": True,
                    "allow_timesheets": True,
                },
                {
                    "name": "Normal Project",
                    "is_template": False,
                    "allow_timesheets": True,
                },
            ]
        )

        self.assertFalse(template_project.account_id, "The template project shouldn't have analytic account")
        self.assertTrue(normal_project.account_id, "A normal project should have a analytic account")

    def test_project_created_from_template_to_have_analytic_account(self):
        template_project_timesheet, template_project_no_timesheet = self.env['project.project'].create([
            {
                "name": "Template Project Timesheet",
                "is_template": True,
                "allow_timesheets": True,
            },
            {
                "name": "Template Project No Timesheet",
                "is_template": True,
                "allow_timesheets": False,
            },
        ])

        new_project_1 = template_project_timesheet.action_create_from_template()
        self.assertTrue(new_project_1.account_id, "A project created from template allowing timesheet should have an analytic account")
        new_project_2 = template_project_no_timesheet.action_create_from_template()
        self.assertFalse(new_project_2.account_id, "A project created from template disabling timesheet should not have an analytic account")

    def test_convert_project_template_into_regular_project_analytics(self):
        template_project = self.env["project.project"].create(
            {
                "name": "Template Project Timesheet",
                "is_template": True,
                "allow_timesheets": True,
            }
        )
        self.assertFalse(template_project.account_id, "The template project shouldn't have analytic account before conversion")
        template_project.action_undo_convert_to_template()
        self.assertFalse(template_project.is_template, "The project should not be a template anymore after conversion")
        self.assertTrue(template_project.account_id, "Converting a template project with timesheets enabled into a regular project should create an analytic account")
