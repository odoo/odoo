# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests.common import tagged

@tagged('-at_install', 'post_install')
class PosSaleGiftCardTest(TestPointOfSaleHttpCommon):

    def test_gift_card_from_sale_order_in_pos(self):
        gift_card = self.env['gift.card'].create({
            'initial_amount': 500,
        })

        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'lst_price': 750,
            'type': 'product',
            'taxes_id': False,
        })

        self.partner1 = self.env['res.partner'].create({
            'name': 'Test',
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner1.id,
            'order_line': [
                Command.create({
                    'product_id': product_A.id,
                    'product_uom_qty': 1,
                    'price_unit': 750,
                }),
            ],
        })

        order._pay_with_gift_card(gift_card)
        order.action_confirm()
        self.main_pos_config.open_session_cb()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderGiftCardSale', login="accountman")
        self.assertEqual(order.pos_order_line_ids[0].order_id.amount_paid, 250, "The amount paid should be 250 because the gift card is 500 and the product is 750")
        self.assertEqual(gift_card.balance, 0, "The gift card balance should be 0 because it has been used")

    def test_gift_card_from_unconfirmed_sale_order_in_pos(self):
        gift_card = self.env['gift.card'].create({
            'initial_amount': 500,
        })

        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'lst_price': 750,
            'type': 'product',
            'taxes_id': False,
        })

        self.partner1 = self.env['res.partner'].create({
            'name': 'Test',
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner1.id,
            'order_line': [
                Command.create({
                    'product_id': product_A.id,
                    'product_uom_qty': 1,
                    'price_unit': 750,
                }),
            ],
        })

        order._pay_with_gift_card(gift_card)
        self.main_pos_config.open_session_cb()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderGiftCardSale', login="accountman")
        self.assertEqual(order.pos_order_line_ids[0].order_id.amount_paid, 250, "The amount paid should be 250 because the gift card is 500 and the product is 750")
        self.assertEqual(gift_card.balance, 0, "The gift card balance should be 0 because it has been used")
