# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.event_booth_sale.tests.common import TestEventBoothSaleCommon
from odoo.tests.common import users
from odoo.tools import float_compare


class TestEventBoothSale(TestEventBoothSaleCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventBoothSale, cls).setUpClass()

        cls.booth_1 = cls.env['event.booth'].create({
            'name': 'Test Booth 1',
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event_0.id,
        })

        cls.booth_2 = cls.env['event.booth'].create({
            'name': 'Test Booth 2',
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event_0.id,
        })

    @users('user_sales_salesman')
    def test_event_booth_prices_with_sale_order(self):
        pricelist = self.env['product.pricelist'].sudo().create({
            'name': 'Test Pricelist',
            'currency_id': self.env.ref('base.USD').id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.event_customer.id,
            'pricelist_id': pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.event_booth_product.id,
                    'event_id': self.event_0.id,
                    'event_booth_category_id': self.event_booth_category_1.id,
                    'event_booth_pending_ids': (self.booth_1 + self.booth_2).ids
                })
            ]
        })

        self.assertEqual(self.event_booth_product.list_price, self.booth_1.price,
                         "Booth price should be equal from product price.")
        # Here we expect the price to be the sum of the booth ($40.0)
        self.assertEqual(float_compare(sale_order.amount_untaxed, 40.0, precision_rounding=0.1), 0,
                         "Untaxed amount should be the sum of the booths prices.")

        self.event_booth_category_1.write({'price': 100.0})
        sale_order.update_prices()

        self.assertNotEqual(self.event_booth_product.list_price, self.booth_1.price,
                            "Booth price should be different from product price.")
        # Here we expect the price to be the sum of the booth ($200.0)
        self.assertEqual(float_compare(sale_order.amount_untaxed, 200.0, precision_rounding=0.1), 0,
                         "Untaxed amount should be the sum of the booths prices.")
