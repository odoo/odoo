# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_gift_card.tests.common import TestSaleGiftCardCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged

@tagged('-at_install', 'post_install')
class TestPayWithGiftCard(TestSaleGiftCardCommon):

    def test_paying_with_single_gift_card(self):
        gift_card = self.env['gift.card'].create({
            'initial_amount': 100,
        })
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        before_gift_card_payment = order.amount_total
        self.assertNotEqual(before_gift_card_payment, 0)
        order._pay_with_gift_card(gift_card)
        order.action_confirm()
        self.assertEqual(before_gift_card_payment - order.amount_total, gift_card.initial_amount - gift_card.balance)

    def test_paying_with_multiple_gift_card(self):
        gift_card_1 = self.env['gift.card'].create({
            'initial_amount': 100,
        })
        gift_card_2 = self.env['gift.card'].create({
            'initial_amount': 100,
        })
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 20.0,
            })
        ]})
        before_gift_card_payment = order.amount_total
        order._pay_with_gift_card(gift_card_1)
        order._pay_with_gift_card(gift_card_2)
        self.assertEqual(order.amount_total, before_gift_card_payment - 200)

    def test_unlink_gift_card_product(self):
        with self.assertRaises(UserError):
            # try to delete several product including pay_with_gift_card_product
            self.env['product.template'].search([('purchase_ok', '=', False), ('sale_ok', '=', False)]).unlink()
