# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon


@odoo.tests.common.tagged('post_install', '-at_install')
class TestConfigurator(TestConfiguratorCommon):

    def test_01_configurator_flow(self):
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})
        self.start_tour('/web#action=website.action_website_configuration', 'configurator_flow', login="admin")
