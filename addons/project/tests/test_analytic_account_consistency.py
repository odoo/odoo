# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import Form, tagged


@tagged('-at_install', 'post_install')
class TestAnalyticAccountConsistency(TestProjectCommon):

    def test_account_consistency_orm_method(self):
        """
        This test ensure that when the user validates his changes in the list view of analytic account, the account
        are correctly removed from their project.
        """

        project_account_id, project_multiple_account = self.env['project.project'].create([{
            "name": "project_account_id",
        }, {
            "name": "project_multiple_account",
        }])
        analytic_plan = self.env['account.analytic.plan'].create({'name': 'secondary plan'})
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        accounts = account_project_plan, account_second_plan = self.env['account.analytic.account'].create([{
            'name': 'account_1', 'company_id': self.env.company.id, 'plan_id': project_plan.id
        }, {
            'name': 'account_2', 'company_id': self.env.company.id, 'plan_id': analytic_plan.id
        }])

        project_account_id.account_id = account_project_plan
        project_multiple_account.account_id = account_project_plan
        project_multiple_account[analytic_plan._column_name()] = account_second_plan

        expected_dict = {'account_id': ['project_account_id', 'project_multiple_account'], 'other_plan': []}
        self.assertDictEqual(expected_dict, self.env['project.project'].get_project_from_account(accounts.ids))

        self.env['project.project'].remove_account_from_projects(accounts.ids)
        self.assertFalse(project_account_id.account_id)
        self.assertFalse(project_multiple_account.account_id)
        self.assertFalse(project_multiple_account[analytic_plan._column_name()])
