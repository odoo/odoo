# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import HttpCase, tagged, loaded_demo_data

_logger = logging.getLogger(__name__)


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
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return

        self.env['delivery.carrier'].create({
            'delivery_type': 'onsite',
            'is_published': True,
            'website_published': True,
            'name': 'Example shipping On Site',
            'product_id': self.env.ref('website_sale_picking.onsite_delivery_product').id,
        })
        self.env.ref("website_sale_picking.payment_provider_onsite").is_published = True

        self.start_tour('/shop', 'onsite_payment_tour')
