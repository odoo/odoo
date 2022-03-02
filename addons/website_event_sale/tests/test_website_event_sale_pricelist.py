# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteEventPriceList(TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super(TestWebsiteEventPriceList, cls).setUpClass()

        cls.WebsiteSaleController = WebsiteSale()

    def test_pricelist_different_currency(self):

        so_line = self.env['sale.order.line'].create({
            'event_id': self.event.id,
            'event_ticket_id': self.ticket.id,
            'name': self.event.name,
            'order_id': self.so.id,
            'product_id': self.ticket.product_id.id,
            'product_uom_qty': 1,
        })
        # set pricelist to 0 - currency: company
        self.pricelist.write({
            'currency_id': self.new_company.currency_id.id,
            'discount_policy': 'with_discount',
            'item_ids': [(5, 0, 0), (0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 0,
            })],
            'name': 'With Discount Included',
        })
        with MockRequest(self.env, sale_order_id=self.so.id, website=self.current_website):
            self.WebsiteSaleController.pricelist(promo=None)
            self.so._cart_update(line_id=so_line.id, product_id=self.ticket.product_id.id, set_qty=1)
        self.assertEqual(so_line.price_reduce, 100)

        # set pricelist to 10% - without discount
        self.pricelist.write({
            'currency_id': self.currency_test.id,
            'discount_policy': 'without_discount',
            'item_ids': [(5, 0, 0), (0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 10,
            })],
            'name': 'Without Discount Included',
        })
        with MockRequest(self.env, sale_order_id=self.so.id, website=self.current_website):
            self.WebsiteSaleController.pricelist(promo=None)
            self.so._cart_update(line_id=so_line.id, product_id=self.ticket.product_id.id, set_qty=1)
        self.assertEqual(so_line.price_reduce, 900, 'Incorrect amount based on the pricelist and its currency.')

        # set pricelist to 10% - with discount
        self.pricelist.write({
            'discount_policy': 'with_discount',
            'name': 'With Discount Included',
        })
        with MockRequest(self.env, sale_order_id=self.so.id, website=self.current_website):
            self.WebsiteSaleController.pricelist(promo=None)
            self.so._cart_update(line_id=so_line.id, product_id=self.ticket.product_id.id, set_qty=1)
        self.assertEqual(so_line.price_reduce, 900, 'Incorrect amount based on the pricelist and its currency.')
