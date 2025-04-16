# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsitePageManager(odoo.tests.HttpCase):

    def test_01_page_manager(self):
        website = self.env['website'].create({
            'name': 'Test Website',
            'domain': '',
            'sequence': 20
        })
        url = self.env['website'].get_client_action_url('/')
        self.start_tour(url, 'website_page_manager', login="admin")
        self.start_tour(url, 'website_page_manager_session_forced', login="admin", cookies={
            'websiteIdMapping': json.dumps({'Test Website': website.id})
        })

        website.domain = self.base_url()
        self.start_tour('/odoo#action=website.action_website_pages_list', 'website_page_manager_direct_access', login='admin')

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

    def test_unique_view_key_on_duplication_pages(self):
        Page = self.env['website.page']
        View = self.env['ir.ui.view']

        test_view = View.create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '<div>Test View</div>',
            'key': 'website.test-duplicate',
        })
        original_page = Page.create({
            'view_id': test_view.id,
            'url': '/test-duplicate',
            'name': 'Test Duplicate',
            'website_id': 1,
        })

        pages = Page.search([('name', 'like', 'Test Duplicate')])
        self.assertEqual(len(pages), 1)

        url = self.env['website'].get_client_action_url('/')
        self.start_tour(url, 'website_clone_pages', login="admin")

        pages = Page.search([('name', 'like', 'Test Duplicate')])
        self.assertEqual(len(pages), 4)

        original_view = View.get_related_views(original_page.view_id.key)

        self.assertEqual(len(original_view), 1)
