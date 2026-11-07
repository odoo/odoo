# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_booth_sale.tests.common import TestEventBoothSaleCommon
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteBoothPriceList(TestEventBoothSaleCommon, TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super(TestWebsiteBoothPriceList, cls).setUpClass()

        cls.WebsiteSaleController = WebsiteSale()
        cls.booth_1 = cls.env['event.booth'].create({
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event.id,
            'name': 'Test Booth 1',
        })

        cls.booth_2 = cls.env['event.booth'].create({
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event.id,
            'name': 'Test Booth 2',
        })

    def test_pricelist_different_currency(self):
        self.env['product.pricelist'].search([('id', '!=', self.pricelist.id)]).action_archive()
        so_line = self.env['sale.order.line'].create({
            'event_booth_category_id': self.event_booth_category_1.id,
            'event_booth_pending_ids': (self.booth_1 + self.booth_2).ids,
            'event_id': self.event.id,
            'order_id': self.so.id,
            'product_id': self.event_booth_product.id,
        })
        # set pricelist to 0 - currency: company
        self.pricelist.write({
            'currency_id': self.env.company.currency_id.id,
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
            self.so._cart_update(line_id=so_line.id, product_id=self.event_booth_product.id, set_qty=1)
        self.assertEqual(so_line.price_reduce_taxexcl, 40)

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
            self.so._cart_update(line_id=so_line.id, product_id=self.event_booth_product.id, set_qty=1)
        self.assertEqual(so_line.price_reduce_taxexcl, 360, 'Incorrect amount based on the pricelist "Without Discount" and its currency.')

        # set pricelist to 10% - with discount
        self.pricelist.write({
            'discount_policy': 'with_discount',
            'name': 'With Discount Included',
        })
        with MockRequest(self.env, sale_order_id=self.so.id, website=self.current_website):
            self.WebsiteSaleController.pricelist(promo=None)
            self.so._cart_update(line_id=so_line.id, product_id=self.event_booth_product.id, set_qty=1)
        self.assertEqual(so_line.price_reduce_taxexcl, 360, 'Incorrect amount based on the pricelist "With Discount" and its currency.')
