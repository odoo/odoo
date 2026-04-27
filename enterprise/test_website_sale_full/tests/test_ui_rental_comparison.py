# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.addons.website_sale_renting.tests.common import TestWebsiteSaleRentingCommon

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestUi(HttpCase, TestWebsiteSaleRentingCommon):

    def test_website_sale_renting_comparison_ui(self):
        # Checkout process in the tour assumes partner information is set.
        self.env.ref('base.user_admin').partner_id.write({
            'country_id': self.env.ref('base.be').id,
            'street': 'StreetName 3',
            'email': 'mitchell.admin@openerp.com',
            'city': 'Louvain-La-Neuve',
            'zip': '1348',
            'phone': '+32 2 290 34 90',
        })
        attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 10,
            'display_type': 'color',
            'value_ids': [
                Command.create({
                    'name': 'Red',
                }),
                Command.create({
                    'name': 'Pink',
                }),
            ]
        })
        self.env['product.template'].create({
            'name': 'Color T-Shirt',
            'list_price': 20.0,
            'website_sequence': 9980,
            'is_published': True,
            'type': 'service',
            'invoice_policy': 'delivery',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': attribute.value_ids,
                })
            ]
        })
        self.attribute_processor = self.env['product.attribute'].create({
            'name': 'Processor',
            'sequence': 1,
        })
        self.values_processor = self.env['product.attribute.value'].create([{
            'name': name,
            'attribute_id': self.attribute_processor.id,
            'sequence': i,
        } for i, name in enumerate(['i3', 'i5', 'i7'])])
        self.attribute_line_processor = self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': self.computer.product_tmpl_id.id,
            'attribute_id': self.attribute_processor.id,
            'value_ids': [(6, 0, v.ids)],
        } for v in self.values_processor])
        self.computer.is_published = True
        self.start_tour("/odoo", 'shop_buy_rental_product_comparison', login='admin')
