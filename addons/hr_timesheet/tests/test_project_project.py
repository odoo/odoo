# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestProjectProject(TransactionCase):

    def test_create_projects(self):
        """
            Test creating some projects and check analytic account generated

            Test case:
            =========
            - Create 4 projects and 2 of them should have timesheets feature enabled
            - Check the projects with timesheets enabled have an analytic account generated
        """
        project1, project2, project3, project4 = self.env['project.project'].create([{
            'name': 'Project 1 (no timesheets)',
            'allow_timesheets': False,
        }, {
            'name': 'Project 2 (timesheets)',
            'allow_timesheets': True,
        }, {
            'name': 'Project 3 (no timesheets)',
            'allow_timesheets': False,
        }, {
            'name': 'Project 4 (timesheets)',
            'allow_timesheets': True,
        }])

        self.assertFalse(project1.account_id, 'Project 1 should not have an analytic account')
        self.assertTrue(project2.account_id, 'Project 2 should have an analytic account')
        self.assertEqual(
            project2.name,
            project2.account_id.name,
            'Project 2 should have the same name as its analytic account'
        )
        self.assertFalse(project3.account_id, 'Project 3 should not have an analytic account')
        self.assertTrue(project4.account_id, 'Project 4 should have an analytic account')
        self.assertEqual(
            project4.name,
            project4.account_id.name,
            'Project 4 should have the same name as its analytic account'
        )

    def test_create_projects_with_default_analytic_account(self):
        project_plan_id = int(self.env['ir.config_parameter'].sudo().get_param('analytic.analytic_plan_projects'))
        if not project_plan_id:
            project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
            project_plan_id = project_plan.id
        analytic_account = self.env['account.analytic.account'].create({'name': 'Test Analytic Account', 'plan_id': project_plan_id})
        project1, project2 = self.env['project.project'].with_context(default_account_id=analytic_account.id).create([{
            'name': 'Project 1 (no timesheets)',
            'allow_timesheets': False,
            'account_id': analytic_account.id,
        }, {
            'name': 'Project 2 (timesheets)',
            'allow_timesheets': True,
            'account_id': analytic_account.id,
        }])
        self.assertEqual(project1.account_id, analytic_account, 'Project 1 should have the default analytic account')
        self.assertEqual(project2.account_id, analytic_account, 'Project 2 should have the default analytic account')
