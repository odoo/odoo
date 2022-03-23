# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestUi(HttpCase):
    def test_onsite_payment_tour(self):
        # Make sure at least one onsite payment option exists.
        self.env['delivery.carrier'].create({
            'delivery_type': 'onsite',
            'website_published': True,
            'name': 'Example shipping method',
            'product_id': self.env.ref('website_sale_picking.onsite_delivery_product').id
        })
        self.start_tour('/shop', 'onsite_payment_tour', login='admin')
