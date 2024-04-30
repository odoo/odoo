# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.addons.website.tools import MockRequest
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteMenu(HttpCase):

    def test_menu_active_element(self):
        records = self.env['test.model'].create([{
            'name': "Record 1",
            'is_published': True,
        }, {
            'name': "Record 2",
            'is_published': True,
        }])

        controller_url = '/test_website/model_item/'
        website = self.env['website'].browse(1)

        self.env['website.menu'].create([{
            'name': records[0].name,
            'url': f"{controller_url}{records[0].id}",
            'parent_id': website.menu_id.id,
            'website_id': website.id,
            'sequence': 10,
        }, {
            'name': records[1].name,
            'url': f"{controller_url}{records[1].id}",
            'parent_id': website.menu_id.id,
            'website_id': website.id,
            'sequence': 20,
        }])
        for record in records:
            record_url = f"{controller_url}{record.id}"
            with MockRequest(self.env, website=website, url_root='', path=record_url):
                tree = html.fromstring(self.env['ir.qweb']._render('test_website.model_item', {
                    'record': record,
                    'main_object': record,
                }))
                menu_link_el = tree.xpath(".//*[@id='top_menu']//a[@href='%s' and contains(@class, 'active')]" % record_url)
                self.assertEqual(len(menu_link_el), 1, "The menu link related to the current record should be active")
