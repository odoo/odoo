# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

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
