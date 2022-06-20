# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_booth.tests.common import TestEventBoothCommon
from odoo.addons.event_sale.tests.common import TestEventSaleCommon


class TestEventBoothSaleCommon(TestEventBoothCommon, TestEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventBoothSaleCommon, cls).setUpClass()

        cls.event_booth_product = cls.env['product.product'].create({
            'name': 'Test Booth Product',
            'description_sale': 'Mighty Booth Description',
            'list_price': 20,
            'standard_price': 60.0,
            'detailed_type': 'event_booth',
        })
        (cls.event_booth_category_1 + cls.event_booth_category_2).write({
            'product_id': cls.event_booth_product.id,
        })

        cls.tax_10 = cls.env['account.tax'].sudo().create({
            'name': 'Tax 10',
            'amount': 10,
        })

        cls.test_pricelist = cls.env['product.pricelist'].sudo().create({
            'name': 'Test Pricelist',
        })
