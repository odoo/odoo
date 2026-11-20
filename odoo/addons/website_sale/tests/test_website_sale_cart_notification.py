# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.common import ProductAttributesCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleCartNotification(HttpCase, ProductAttributesCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        self.start_tour("/", 'website_sale_cart_notification')
