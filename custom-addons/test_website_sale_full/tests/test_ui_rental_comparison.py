# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import HttpCase, tagged, loaded_demo_data
from odoo.addons.website_sale_renting.tests.common import TestWebsiteSaleRentingCommon

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestUi(HttpCase, TestWebsiteSaleRentingCommon):

    def test_website_sale_renting_comparison_ui(self):
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
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
        self.start_tour("/web", 'shop_buy_rental_product_comparison', login='admin')
