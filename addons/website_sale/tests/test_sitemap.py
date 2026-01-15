# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSitemap(HttpCase):

    def setUp(self):
        super(TestSitemap, self).setUp()

        self.cats = self.env['product.public.category'].create([{
            'name': 'Level 0',
        }, {
            'name': 'Level 1',
        }, {
            'name': 'Level 2',
        }])
        self.cats[2].parent_id = self.cats[1].id
        self.cats[1].parent_id = self.cats[0].id
        # 'Level 2' cetegory must have at least one published product to be visible by public users
        self.env['product.product'].create({
            'name': 'Dummy product',
            'list_price': 100.0,
            'public_categ_ids': [Command.link(self.cats[2].id)],
            'is_published': True,
        })

    def test_01_shop_route_sitemap(self):
        resp = self.url_open('/sitemap.xml')
        level2_url = '/shop/category/level-0-level-1-level-2-%s' % self.cats[2].id
        self.assertIn(level2_url, resp.text, "Category entry in sitemap should be prefixed by its parent hierarchy.")
