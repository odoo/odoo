# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import Form, tagged
from odoo.exceptions import UserError

@tagged('-at_install', 'post_install')
class TestAnalyticAccountConsistency(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_plan, cls.other_plans = cls.env['account.analytic.plan']._get_all_plans()
        cls.second_plan = cls.other_plans[0] if cls.other_plans else cls.env['account.analytic.plan'].create({'name': 'secondary plan'})
        cls.project_plan_child_1, cls.project_plan_child_2, cls.second_plan_child = cls.env['account.analytic.plan'].create([{
            'name': 'Project Plan Child 1',
            'parent_id': cls.project_plan.id,
        }, {
            'name': 'Project Plan Child 2',
            'parent_id': cls.project_plan.id,
        }, {
            'name': 'Second Plan Child',
            'parent_id': cls.second_plan.id,
        }])
        cls.accounts = (cls.account_project_plan, cls.account_second_plan, cls.account_project_plan_child_1,
                        cls.account_project_plan_child_2, cls.account_second_plan_child) \
            = cls.env['account.analytic.account'].create([{
                'name': 'account_project_plan', 'company_id': cls.env.company.id, 'plan_id': cls.project_plan.id
            }, {
                'name': 'account_project_plan', 'company_id': cls.env.company.id, 'plan_id': cls.second_plan.id
            }, {
                'name': 'account_project_plan_child_1', 'company_id': cls.env.company.id, 'plan_id': cls.project_plan_child_1.id
            }, {
                'name': 'account_project_plan_child_2', 'company_id': cls.env.company.id, 'plan_id': cls.project_plan_child_2.id
            }, {
                'name': 'account_second_plan_child', 'company_id': cls.env.company.id, 'plan_id': cls.second_plan_child.id
            }])

    def test_get_projects_name_from_account(self):
        """
        this test ensures that the method get_projects_name_from_account return the correct values.
        """
        second_plan_column_name = self.second_plan._column_name()
        project_root_account, project_second_child, project_wrong_root_account, project_wrong_child, project_multiple_accounts \
            = self.env['project.project'].create([{
                'name': 'project account id',
                'account_id': self.account_project_plan.id,
            }, {
                'name': 'project account child 2',
                'account_id': self.account_project_plan_child_2.id,
            }, {
                'name': 'project account second plan',
                second_plan_column_name: self.account_second_plan.id,
            }, {
                'name': 'project account second plan child',
                second_plan_column_name: self.account_second_plan_child.id,
            }, {
                'name': 'project_multiple_account',
                'account_id': self.account_project_plan.id,
                second_plan_column_name: self.account_second_plan.id,
            }])

        self.assertDictEqual(
            {'account_id': [], 'other_plan': ['project account second plan', 'project account second plan child', 'project_multiple_account']},
            project_root_account.get_projects_name_from_account(self.accounts.ids, self.project_plan_child_1.id)
        )
        self.assertDictEqual(
            {'account_id': ['project account child 2', 'project account id', 'project_multiple_account'], 'other_plan': []},
            project_root_account.get_projects_name_from_account(self.accounts.ids, self.second_plan_child.id)
        )

    def test_account_removal_from_projects(self):
        """
        This test ensures that the method remove_accounts_from_projects correctly removes the account from
        their projects when it is needed.
        """
        second_plan_column_name = self.second_plan._column_name()
        project_root_account, project_second_child, project_wrong_root_account, project_wrong_child, project_multiple_accounts\
            = self.env['project.project'].create([{
                'name': 'project account id',
                'account_id': self.account_project_plan.id,
            }, {
                'name': 'project account child 2',
                'account_id': self.account_project_plan_child_2.id,
            }, {
                'name': 'project account second plan',
                second_plan_column_name: self.account_second_plan.id,
            }, {
                'name': 'project account second plan child',
                second_plan_column_name: self.account_second_plan_child.id,
            }, {
                'name': 'project_multiple_account',
                'account_id': self.account_project_plan.id,
                second_plan_column_name: self.account_second_plan.id,
            }])
        project_root_account.remove_accounts_from_projects(self.accounts.ids, self.project_plan_child_1.id)

        self.assertFalse(project_multiple_accounts[second_plan_column_name])
        self.assertFalse(project_wrong_root_account[second_plan_column_name])
        self.assertFalse(project_wrong_child[second_plan_column_name])

        self.assertEqual(project_root_account.account_id, self.account_project_plan)
        self.assertEqual(project_second_child.account_id, self.account_project_plan_child_2)
        self.assertEqual(project_multiple_accounts.account_id, self.account_project_plan)

    def test_raise_error_with_invalid_account(self):
        """
        This test ensures that when the user validates his change on project(s), an error is raised when an account is
        set on the wrong plan field.
        """
        project = self.env['project.project'].create({
            'name': 'new project',
            'account_id': self.account_project_plan_child_1.id,
        })

        # updating from one child to another is valid
        project.account_id = self.account_project_plan_child_2

        with self.assertRaises(UserError, msg="The account set on the project does not have a matching plan."):
            project.account_id = self.account_second_plan

        with self.assertRaises(UserError, msg="The account set on the project does not have a matching plan."):
            project.account_id = self.account_second_plan_child

    def test_raise_error_on_plan_update(self):
        """This test ensures that when a user update the plan of an analytic account, an error is raised if the account
        is linked to a project"""

        self.env['project.project'].create({
            'name': 'new project',
            'account_id': self.account_project_plan_child_1.id,
        })

        # updating from one child to another is valid
        self.account_project_plan_child_1.plan_id = self.project_plan_child_2

        with self.assertRaises(UserError, msg="The plan set on the account does not match with its project."):
            self.account_project_plan_child_1.plan_id = self.second_plan

        with self.assertRaises(UserError, msg="The plan set on the account does not match with its project."):
            self.account_project_plan_child_1.plan_id = self.second_plan_child
