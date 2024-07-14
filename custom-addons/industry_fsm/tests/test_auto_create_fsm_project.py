# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.tests.common import TransactionCase, new_test_user
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestAutoCreateFsmProject(TransactionCase):

    def test_auto_create_fsm_task(self):
        """ Test Field Service automatically created project when a company is created

            Test Case:
            =========
            1) Assert first company is created with Field Service project
            2) Add second company and assert second Field Service project is created
            3) Create new user with allowed_company_ids = [first_company, second_company]
            4) Get Field Service Project with the 2 companies and assert project display name has this format "Field Service - {Company Name}"
        """
        fsm_projects = self.env['project.project'].search([('is_fsm', '=', True)])
        fsm_projects_count = len(fsm_projects)

        fsm_project = fsm_projects[0]
        fsm_project_name = 'Field Service'
        first_company = fsm_project.company_id

        self.assertEqual(fsm_project_name, fsm_project.display_name)

        second_company = self.env['res.company'].create(
            {
                'name': 'New Company',
            }
        )

        fsm_projects_count += 1

        fsm_projects = self.env['project.project'].search([('is_fsm', '=', True)])
        self.assertEqual(fsm_projects_count, len(fsm_projects), 'New fsm project automatically created when new company is created')

        second_fsm_project = next(project for project in fsm_projects if project.id != fsm_project.id and project.company_id.id == second_company.id)
        fsm_project = next(project for project in fsm_projects if project.id == fsm_project.id and project.company_id.id == first_company.id)

        self.assertTrue(all(project.name == fsm_project_name for project in fsm_projects))
        self.assertEqual(first_company, fsm_project.company_id)
        self.assertEqual(second_company, second_fsm_project.company_id)

        user = new_test_user(self.env, login='bub', groups='hr.group_hr_user',
                             company_id=first_company.id,
                             company_ids=[(6, 0, (first_company + second_company).ids)])

        fsm_projects = self.env['project.project'].with_user(user).with_context(allowed_company_ids=[first_company.id, second_company.id]).search([('is_fsm', '=', True)])
        second_fsm_project = next(project for project in fsm_projects if project.id != fsm_project.id and project.company_id.id == second_company.id)
        fsm_project = next(project for project in fsm_projects if project.id == fsm_project.id and project.company_id.id == first_company.id)
        self.assertEqual("{} - {}".format(fsm_project_name, first_company.name), fsm_project.display_name)
        self.assertEqual("{} - {}".format(fsm_project_name, second_company.name), second_fsm_project.display_name)

    def test_multi_create_fsm(self):
        second_company = self.env['res.company'].create({'name': 'New Company'})
        default_project, default_project_with_company, fsm_project_company_2, fsm_project_main_company = self.env['project.project'].create([{
            'name': 'Basic project',
        }, {
            'name': 'Basic project company 2',
            'company_id': second_company.id,
        }, {
            'name': 'FSM project company 2',
            'company_id': second_company.id,
            'is_fsm': True,
        }, {
            'name': 'FSM project main company ',
            'company_id': self.env.company.id,
            'is_fsm': True,
        }])
        self.assertFalse(default_project.company_id, "No company should have been set for the default project.")
        self.assertEqual(second_company, default_project_with_company.company_id, "The company given in the vals_list should be the company of the project.")
        self.assertEqual(second_company, fsm_project_company_2.company_id, "The company given in the vals_list should be the company of the project.")
        self.assertEqual(self.env.company, fsm_project_main_company.company_id, "The company given in the vals_list should be the company of the project.")
