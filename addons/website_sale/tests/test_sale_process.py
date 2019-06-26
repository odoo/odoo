# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_01_admin_shop_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop.ready", login="admin")

    def test_02_admin_checkout(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop_buy_product')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop_buy_product.ready", login="admin")

    def test_03_demo_checkout(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop_buy_product')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop_buy_product.ready", login="demo")


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteSaleCheckoutAddress(odoo.tests.TransactionCase):
    def test_01_edit_billing_address(self):
        website = self.env['website'].browse(1)
        p = self.env.user.partner_id
        so = self.env['sale.order'].create({
            'partner_id': p.id,
            'website_id': website.id,
            'order_line': [(0, 0, {
                'product_id': self.env['product.product'].create({'name': 'Product A', 'list_price': 100}).id,
                'name': 'Product A',
            })]
        })
        country_id = self.env['res.country'].search([], limit=1).id

        WebsiteSaleController = WebsiteSale()
        with MockRequest(self.env, website=website, sale_order_id=so.id):
            WebsiteSaleController.address(name='website_sale test user', email='email@email.email', street='ooo', city='ooo', country_id=country_id, submitted=1, partner_id=p.id)
            self.assertFalse(p.website_id, "Partner should not have a website set on him after editing billing.")

        website.specific_user_account = True
        with MockRequest(self.env, website=website, sale_order_id=so.id):
            WebsiteSaleController.address(name='website_sale test user', email='email@email.email', street='ooo', city='ooo', country_id=country_id, submitted=1, partner_id=p.id)
            self.assertEqual(p.website_id, website, "Partner should have a website set on him after editing billing.")
