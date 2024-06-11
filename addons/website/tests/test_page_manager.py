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

        alternate_website = self.env['website'].search([('name', '=', 'My Website 2')], limit=1)
        alternate_website.domain = f'http://{HOST}:{config["http_port"]}'
        self.start_tour('/web#action=website.action_website_pages_list', 'website_page_manager_direct_access', login='admin')

    def test_generic_page_diverged_not_shown(self):
        Page = self.env['website.page']
        Website = self.env['website']

        website = Website.browse(1)
        generic_page = Page.create({
            'name': 'Test Diverged',
            'type': 'qweb',
            'arch': '''
                <div>content</div>
            ''',
            'key': "test.test_diverged",
            'url': "/test_diverged",
            'is_published': True,
        })
        # trigger cow page creation
        generic_page.with_context(website_id=website.id).arch_db = '<div>COW content</div>'
        specific_page = Page.search([('url', '=', '/test_diverged'), ('website_id', '=', website.id)], limit=1)
        self.assertNotEqual(generic_page, specific_page)
        locs = website.with_context(website_id=website.id)._enumerate_pages(query_string="/test_diverged")
        self.assertEqual(len(list(locs)), 1, "Specific page should be shown as same url")
        specific_page.url = '/something_else'
        locs = website.with_context(website_id=website.id)._enumerate_pages(query_string="/test_diverged")
        self.assertEqual(len(list(locs)), 0, "Specific page should not be shown as not matching the requested URL and generic should not be shown either as it is shadowed by specific")

        # test that generic is still shown on other website
        website_2 = Website.create({'name': 'website 2'})
        locs = website_2.with_context(website_id=website_2.id)._enumerate_pages(query_string="/test_diverged")
        self.assertEqual(len(list(locs)), 1, "Generic page should be shown")
