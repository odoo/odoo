# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.tests.common import HOST
from odoo.tools import config


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsitePageManager(odoo.tests.HttpCase):

    def test_01_page_manager(self):
        if self.env['website'].search_count([]) == 1:
            self.env['website'].create({
                'name': 'My Website 2',
                'domain': '',
                'sequence': 20,
            })
        url = self.env['website'].get_client_action_url('/')
        self.start_tour(url, 'website_page_manager', login="admin")
        self.start_tour(url, 'website_page_manager_session_forced', login="admin")

        alternate_website = self.env['website'].search([], limit=2)[1]
        alternate_website.domain = f'http://{HOST}:{config["http_port"]}'
        self.start_tour('/web#action=website.action_website_pages_list', 'website_page_manager_direct_access', login='admin')
