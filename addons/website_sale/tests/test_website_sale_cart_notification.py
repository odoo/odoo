# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleCartNotification(HttpCase, ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.company.website_id
        cls.size_attribute.create_variant = 'no_variant'
        cls.product_tmpl_1 = cls.env['product.template'].create({
            'name': 'website_sale_cart_notification_product_1',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000,
        })
        cls.product_tmpl_2 = cls.env['product.template'].create({
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

    def test_website_sale_cart_notification_tax_included(self):
        self.env.ref('website_sale.product_search').active = True
        self.website.show_line_subtotals_tax_selection = 'tax_included'
        self.start_tour("/", 'website_sale_cart_notification_tax_included')

    def test_website_sale_cart_notification_tax_excluded(self):
        self.env.ref('website_sale.product_search').active = True
        self.website.show_line_subtotals_tax_selection = 'tax_excluded'
        self.start_tour("/", 'website_sale_cart_notification_tax_excluded')

    def test_website_sale_cart_notification_qty_and_total(self):
        """ Check that adding product into cart which is already in the cart only display newly
        added qty count and total."""

        self.env.ref('website_sale.product_search').active = True
        self.start_tour("/", 'website_sale_cart_notification_qty_and_total')
