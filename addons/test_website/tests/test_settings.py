# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests

@odoo.tests.tagged('-at_install', 'post_install')
class TestWebsiteSettings(odoo.tests.HttpCase):
    def test_01_multi_website_settings(self):
        self.env['website'].create({'name': "Website Test Settings", 'specific_user_account': True})
        self.start_tour("/web", 'website_settings_m2o_dirty', login="admin")
