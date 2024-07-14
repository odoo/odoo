# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from .common import TestWebsiteSaleRentingCommon
from freezegun import freeze_time

@tagged('-at_install', 'post_install')
class TestUi(HttpCase, TestWebsiteSaleRentingCommon):

    def test_website_sale_renting_ui(self):
        self.env.ref('base.user_admin').write({
            'name': 'Mitchell Admin',
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
        })
        self.start_tour("/web", 'shop_buy_rental_product', login='admin')

    def test_add_accessory_rental_product(self):
        parent_product, accessory_product = self.env['product.product'].create([
            {
                'name': 'Parent product',
                'list_price': 2000,
                'rent_ok': True,
                'is_published': True,
            },
            {
                'name': 'Accessory product',
                'list_price': 2000,
                'rent_ok': True,
                'is_published': True,
            }
        ])
        recurrence = self.env['sale.temporal.recurrence'].sudo().create({'duration': 1, 'unit': 'hour'})
        self.env['product.pricing'].create([
            {
                'recurrence_id': recurrence.id,
                'price': 1000,
                'product_template_id': parent_product.product_tmpl_id.id,
            },
            {
                'recurrence_id': recurrence.id,
                'price': 1000,
                'product_template_id': accessory_product.product_tmpl_id.id,
            },
        ])
        parent_product.accessory_product_ids = accessory_product
        self.start_tour("/web", 'shop_buy_accessory_rental_product', login='admin')

    def test_website_sale_renting_default_range(self):
        with freeze_time("2023-12-04 08:00"):
            self.start_tour('/web', 'website_sale_renting_default_duration_from_default_range', login='admin')
