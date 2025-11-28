# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.controllers.cart import Cart


@tagged('post_install', '-at_install')
class TestWebsiteSaleCartNotification(HttpCase, ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteSaleCartController = Cart()
        cls.size_attribute.create_variant = 'no_variant'
        cls.env['product.template'].create({
            'name': 'website_sale_cart_notification_product_1',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000,
        })
        cls.env['product.template'].create({
            'name': 'website_sale_cart_notification_product_2',
            'type': 'consu',
            'website_published': True,
            'list_price': 5000,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.size_attribute.id,
                'value_ids': [Command.set([
                    cls.size_attribute_s.id,
                    cls.size_attribute_m.id,
                    cls.size_attribute_l.id,
                ])],
            })],
        })

    def test_website_sale_cart_notification(self):
        self.env.ref('website_sale.product_search').active = True
        self.start_tour('/', 'website_sale.cart_notification')

    def test_website_sale_cart_notification_qty_and_total(self):
        """Check that adding product into cart which is already in the cart only display newly
        added qty count and total.
        """
        self.env.ref('website_sale.product_search').active = True
        self.start_tour('/', 'website_sale.cart_notification_qty_and_total')

    def test_website_sale_cart_notification_product_price(self):
        """Check that the cart notification displays the correct total price included/excluded taxes
        depending on the website settings.
        """
        website = self.env['website'].get_current_website()
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'website_id': website.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                }),
            ]
        })
        added_qty_per_line = {sale_order.order_line.id: 1.0}
        website.show_line_subtotals_tax_selection = 'tax_included'
        price_tax_included = self.WebsiteSaleCartController._get_cart_notification_information(
            sale_order, added_qty_per_line
        )['lines'][0]['price_total']
        self.assertEqual(price_tax_included, 23)
        website.show_line_subtotals_tax_selection = 'tax_excluded'
        price_tax_excluded = self.WebsiteSaleCartController._get_cart_notification_information(
            sale_order, added_qty_per_line
        )['lines'][0]['price_total']
        self.assertEqual(price_tax_excluded, 20)
