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
