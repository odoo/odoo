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
        template_project = self.env['project.project'].create({
            "name": "Template Project",
            "is_template": True,
            "allow_timesheets": True,
        })

        new_project = template_project.action_create_from_template()
        self.assertTrue(new_project.account_id, "A project created from template should have a analytic account")
