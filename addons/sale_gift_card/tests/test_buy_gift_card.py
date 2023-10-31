# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_gift_card.tests.common import TestSaleGiftCardCommon
from odoo.tests.common import tagged

@tagged('-at_install', 'post_install')
class TestBuyGiftCard(TestSaleGiftCardCommon):

    def test_buying_simple_gift_card(self):
        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_gift_card.id,
                'name': 'Gift Card Product',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(order.gift_card_count, 0)
        self.assertEqual(len(order.order_line.mapped('generated_gift_card_ids')), 0)
        order.action_confirm()
        # After Confirmation
        self.assertEqual(order.gift_card_count, 1)
        self.assertEqual(len(order.order_line.mapped('generated_gift_card_ids')), 1)

    def test_buying_multiple_gift_card(self):
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            Command.create({
                'product_id': self.product_gift_card.id,
                'name': 'Gift Card Product',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            Command.create({
                'product_id': self.product_gift_card.id,
                'name': 'Gift Card Product',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.assertEqual(order.gift_card_count, 0)
        self.assertEqual(len(order.order_line.mapped('generated_gift_card_ids')), 0)
        order.action_confirm()
        # After Confirmation
        self.assertEqual(order.gift_card_count, 2)
        self.assertEqual(len(order.order_line.mapped('generated_gift_card_ids')), 2)
