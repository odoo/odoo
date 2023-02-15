# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestUi(HttpCase):
    def setUp(self):
        super(TestUi, self).setUp()
        # create a Chair floor protection product
        self.env['product.product'].create({
            'name': 'Chair floor protection',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000,
        })
        # create a Customizable Desk product
        self.env['product.product'].create({
            'name': 'Customizable Desk',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000,
        })
        # create a Warranty product
        self.env['product.product'].create({
            'name': 'Warranty',
            'type': 'service',
            'website_published': True,
            'list_price': 20,
        })

    def test_onsite_payment_tour(self):
        # Make sure at least one onsite payment option exists.
        self.env['delivery.carrier'].create({
            'delivery_type': 'onsite',
            'is_published': True,
            'website_published': True,
            'name': 'Example shipping On Site',
            'product_id': self.env.ref('website_sale_picking.onsite_delivery_product').id,
        })
        self.env.ref("website_sale_picking.payment_provider_onsite").is_published = True

        self.start_tour('/shop', 'onsite_payment_tour')
