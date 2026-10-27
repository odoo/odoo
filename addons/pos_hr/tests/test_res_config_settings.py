# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import Command
from odoo.tests import new_test_user
from odoo.addons.pos_hr.tests.test_frontend import TestPosHrHttpCommon
from odoo.addons.point_of_sale.tests.test_res_config_settings import TestConfigureShops


@odoo.tests.tagged('post_install', '-at_install')
class TestConfigureShopsPoSHR(TestPosHrHttpCommon, TestConfigureShops):
    def test_properly_deleting_pos_hr_group_all_members(self):
        self._remove_on_payment_taxes()

        # Simulate removing all employees from `basic_employee_ids` and
        # `minimal_employee_ids`. Equivalent to passing an empty command list `[]`.
        self.main_pos_config.with_context(from_settings_view=True).write({
            'basic_employee_ids': [],
            'minimal_employee_ids': []
        })

        self.assertListEqual(self.main_pos_config.basic_employee_ids.ids, [])
        self.assertListEqual(self.main_pos_config.minimal_employee_ids.ids, [])

    def test_advanced_employees_kept_on_later_write(self):
        """
        Another misc write on the same config, coming from an override,
        should not drop the previously set advanced_employee_ids.
        """
        employees = self.env['hr.employee'].create([{'name': 'Employee A'}, {'name': 'Employee B'}])
        config = self.main_pos_config.with_context(from_settings_view=True)

        config.write({'advanced_employee_ids': [Command.link(emp.id) for emp in employees]})
        advanced_employees = config.advanced_employee_ids
        self.assertTrue(employees <= advanced_employees)

        config.write({})
        self.assertEqual(config.advanced_employee_ids, advanced_employees)

    def test_write_create_employee_if_none(self):
        """This test make sure that the employee set on advanced_employee_ids is from
           the current company. And if none exists it create one for the user."""

        # First test that an employee is created if none exists
        self.env['hr.employee'].search([]).unlink()
        self.main_pos_config.with_context(from_settings_view=True).write({
            'basic_employee_ids': [],
        })

        self.assertEqual(len(self.main_pos_config.advanced_employee_ids), 1)
        self.assertEqual(self.main_pos_config.advanced_employee_ids.company_id, self.main_pos_config.company_id)
        advanced_employee = self.main_pos_config.advanced_employee_ids

        # Test that the previously employee is used
        self.main_pos_config.with_context(from_settings_view=True).write({
            'advanced_employee_ids': [],
        })
        self.assertEqual(len(self.main_pos_config.advanced_employee_ids), 1)
        self.assertEqual(self.main_pos_config.advanced_employee_ids.company_id, self.main_pos_config.company_id)
        self.assertEqual(self.main_pos_config.advanced_employee_ids, advanced_employee)

    def test_settings_advanced_employees_from_config_company(self):
        """Saving the settings of a PoS of another company than the current one
           must only add the PoS managers' employees of the PoS company."""
        self._remove_on_payment_taxes()
        branch = self.env['res.company'].create({
            'name': 'Branch 1',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
        })
        branch_config = self.env['pos.config'].with_company(branch).create({'name': 'Branch Point of Sale'})
        # PoS manager with an employee in each company; current company stays the main one
        self.pos_admin.company_ids += branch
        branch_admin = self.env['hr.employee'].create({
            'name': 'Branch Admin',
            'company_id': branch.id,
            'user_id': self.pos_admin.id,
        })
        self.assertEqual(self.manager1.company_id, self.env.company)

        self.env['res.config.settings'].create({'pos_config_id': branch_config.id}).execute()

        self.assertIn(branch_admin, branch_config.advanced_employee_ids)
        self.assertNotIn(self.manager1, branch_config.advanced_employee_ids)
        self.assertEqual(branch_config.advanced_employee_ids.company_id, branch)

    def test_multi_config_write_keeps_managers_per_company(self):
        """Writing on configs of different companies must only add the PoS
           managers of each config's own company."""
        branch = self.env['res.company'].create({
            'name': 'Branch 1',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
        })
        branch_config = self.env['pos.config'].with_company(branch).create({'name': 'Branch Point of Sale'})
        branch_manager_user = new_test_user(
            self.env,
            login="branch_manager_user",
            groups="point_of_sale.group_pos_manager",
            company_id=branch.id,
            company_ids=[Command.set(branch.ids)],
        )
        branch_manager = self.env['hr.employee'].create({
            'name': 'Branch Manager',
            'company_id': branch.id,
            'user_id': branch_manager_user.id,
        })
        configs = self.main_pos_config + branch_config
        configs.write({'name': 'Multi-write'})
        configs.sudo().write({'name': 'Multi-write sudo'})
        branch_config.with_context(from_settings_view=True).write({'name': 'Branch settings'})

        self.assertIn(self.manager1, self.main_pos_config.advanced_employee_ids)
        self.assertIn(self.manager2, self.main_pos_config.advanced_employee_ids)
        self.assertNotIn(branch_manager, self.main_pos_config.advanced_employee_ids)
        self.assertEqual(self.main_pos_config.advanced_employee_ids.company_id, self.env.company)
        self.assertIn(branch_manager, branch_config.advanced_employee_ids)
        self.assertNotIn(self.manager1, branch_config.advanced_employee_ids)
        self.assertNotIn(self.manager2, branch_config.advanced_employee_ids)
        self.assertEqual(branch_config.advanced_employee_ids.company_id, branch)

    def test_multi_config_write_does_not_mutate_vals(self):
        vals = {'name': 'Multi-write', 'advanced_employee_ids': [Command.link(self.emp4.id)]}
        second_config = self.main_pos_config.copy()
        (self.main_pos_config + second_config).write(vals)
        self.assertEqual(vals, {'name': 'Multi-write', 'advanced_employee_ids': [Command.link(self.emp4.id)]})
