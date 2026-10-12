# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteDuplicate(HttpCase):

    def test_duplicate_website(self):
        website = self.env['website'].create({
            'name': 'Source Website',
            'domain': 'https://source.example.com',
        })
        View = self.env['ir.ui.view']
        View.create({
            'name': 'Duplicate Layout',
            'type': 'qweb',
            'key': 'website.test_duplicate_layout',
            'inherit_id': self.env.ref('website.layout').id,
            'website_id': website.id,
            'arch': '<xpath expr="//main" position="before"><div class="o_test_duplicate_layout"/></xpath>',
        })
        page = self.env['website.page'].create({
            'name': 'Duplicate Page',
            'type': 'qweb',
            'key': 'website.test_duplicate_page',
            'url': '/duplicate-page',
            'arch': '<t t-call="website.layout"><div id="wrap">Duplicate page content</div></t>',
            'website_id': website.id,
            'is_published': True,
        })
        self.env['website.menu'].create({
            'name': 'Duplicate Menu',
            'page_id': page.id,
            'parent_id': self.env.ref(website._website_xmlid('website.main_menu')).id,
            'website_id': website.id,
        })

        duplicate = website.copy()

        self.assertEqual(
            sorted(View.search([('website_id', '=', duplicate.id)]).mapped('key')),
            sorted(View.search([('website_id', '=', website.id)]).mapped('key')),
        )
        duplicate.domain = self.base_url()
        html = self.url_open('/duplicate-page').text
        self.assertIn(f'data-website-id="{duplicate.id}"', html)
        self.assertIn('Duplicate page content', html)
        self.assertIn('o_test_duplicate_layout', html)
        self.assertIn('Duplicate Menu', html)
