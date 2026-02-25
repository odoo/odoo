# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.sale_gelato.tests.test_sale_order import TestGelatoSaleOrder
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.website_sale_gelato.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestGelatoCheckoutAddress(TestGelatoSaleOrder, WebsiteSaleCommon):
    def setUp(self):
        super().setUp()
        self.WebsiteSaleController = WebsiteSale()

    def test_require_editing_too_long_delivery_address(self):
        user = self._create_new_portal_user()
        user.write({'partner_id': self.partner_street_too_long.id})
        website = self.website.with_user(user).with_context({})
        self.gelato_order.write({
            'partner_id': self.partner_street_too_long,
            'website_id': website.id,
        })
        with MockRequest(website.env, website=website, sale_order_id=self.gelato_order.id):
            redirection = self.WebsiteSaleController._check_addresses(self.gelato_order)
            self.assertTrue(redirection is not None)
            self.assertEqual(
                redirection.location,
                f'/shop/address?partner_id={self.partner_street_too_long.id}&address_type=delivery',
            )
