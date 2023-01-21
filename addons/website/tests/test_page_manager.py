# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsitePageManager(odoo.tests.HttpCase):

    def test_01_page_manager(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'website_page_manager', login="admin")
