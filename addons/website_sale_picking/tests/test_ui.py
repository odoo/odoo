# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import HttpCase, tagged

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestUi(HttpCase):
    def setUp(self):
        super(TestUi, self).setUp()
        self.env['product.product'].create([{
            'name': 'Product Consumable',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000,
        }, {
            'name': 'Product Service',
            'type': 'service',
            'website_published': True,
            'list_price': 20,
        }])

    def test_onsite_payment_tour(self):
        self.env['delivery.carrier'].create({
            'delivery_type': 'onsite',
            'is_published': True,
            'website_published': True,
            'name': 'Example shipping On Site',
            'product_id': self.env.ref('website_sale_picking.onsite_delivery_product').id,
        })
        self.env.ref("website_sale_picking.payment_provider_onsite").state = 'enabled'
        self.env.ref("website_sale_picking.payment_provider_onsite").is_published = True

        self.start_tour('/shop', 'onsite_payment_tour')
