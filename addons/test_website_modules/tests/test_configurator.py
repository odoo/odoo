# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.website.tests.test_configurator import TestConfiguratorCommon

@odoo.tests.common.tagged('post_install', '-at_install')
class TestConfigurator(TestConfiguratorCommon):

    def test_01_configurator_flow(self):
        self.start_tour('/web#action=website.action_website_configuration', 'configurator_flow', login="admin")
