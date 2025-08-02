# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('-at_install', 'post_install')
class TestPayWithGiftCard(TestSaleCouponCommon):

    def test_paying_with_single_gift_card_over(self):
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()
        gift_card = self.program_gift_card.coupon_ids[0]
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
        self._apply_promo_code(order, gift_card.code)
        order.action_confirm()
        self.assertEqual(before_gift_card_payment - order.amount_total, 100 - gift_card.points)

    def test_paying_with_single_gift_card_under(self):
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()
        gift_card = self.program_gift_card.coupon_ids[0]
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_B.id,
                'name': 'Ordinary Product b',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        before_gift_card_payment = order.amount_total
        self.assertNotEqual(before_gift_card_payment, 0)
        self._apply_promo_code(order, gift_card.code)
        order.action_confirm()
        self.assertEqual(before_gift_card_payment - order.amount_total, 100 - gift_card.points)

    def test_paying_with_multiple_gift_card(self):
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 2,
            'points_granted': 100,
        }).generate_coupons()
        gift_card_1, gift_card_2 = self.program_gift_card.coupon_ids
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
        self._apply_promo_code(order, gift_card_1.code)
        self._apply_promo_code(order, gift_card_2.code)
        self.assertEqual(order.amount_total, before_gift_card_payment - 200)

    def test_paying_with_gift_card_and_discount(self):
        # Test that discounts take precedence on payment rewards
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 50,
        }).generate_coupons()
        gift_card_1 = self.program_gift_card.coupon_ids
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_C.id,
                'name': 'Ordinary Product C',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.env['loyalty.program'].create({
            'name': 'Code for 10% on orders',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'test_10pc',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        self.assertEqual(order.amount_total, 100)
        self._apply_promo_code(order, gift_card_1.code)
        self.assertEqual(order.amount_total, 50)
        self._apply_promo_code(order, "test_10pc")
        # real flows also have to update the programs and rewards
        order._update_programs_and_rewards()
        self.assertEqual(order.amount_total, 40) # 100 - 10% - 50

    def test_paying_with_gift_card_blocking_discount(self):
        # Test that a payment program making the order total 0 still allows the user to claim discounts
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()
        gift_card_1 = self.program_gift_card.coupon_ids
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_C.id,
                'name': 'Ordinary Product C',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.env['loyalty.program'].create({
            'name': 'Code for 10% on orders',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'test_10pc',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        self.assertEqual(order.amount_total, 100)
        self._apply_promo_code(order, gift_card_1.code)
        self.assertEqual(order.amount_total, 0)
        self._apply_promo_code(order, "test_10pc")
        # real flows also have to update the programs and rewards
        order._update_programs_and_rewards()
        self.assertEqual(order.amount_total, 0) # 100 - 10% - 90

    def test_gift_card_product_has_no_taxes_on_creation(self):
        gift_card_program = self.env['loyalty.program'].create({
            'name': 'Gift Cards',
            'applies_on': 'future',
            'program_type': 'gift_card',
            'trigger': 'auto',
            'rule_ids': [Command.create({
                'product_ids': self.product_gift_card,
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'reward_point_split': True,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 1,
                'discount_mode': 'per_point',
                'discount_applicability': 'order',
            })]
        })
        self.assertFalse(gift_card_program.reward_ids.discount_line_product_id.taxes_id)

    def test_paying_with_gift_card_uses_gift_card_product_taxes(self):
        order = self.empty_order
        order.order_line = [
            Command.create({
                'product_id': self.product_B.id,
                'name': 'Ordinary Product b',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
                'price_unit': 200.0,
            })
        ]
        sol = order.order_line
        before_gift_card_payment = order.amount_total
        self.assertNotEqual(before_gift_card_payment, 0)

        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()
        gift_card = self.program_gift_card.coupon_ids[0]

        # TODO check amount total of gift_card_line

        # TAX EXCL
        self.program_gift_card.reward_ids.discount_line_product_id.taxes_id = [
            Command.link(self.tax_15pc_excl.id)
        ]
        self._apply_promo_code(order, gift_card.code)
        gift_card_line = order.order_line - sol
        self.assertAlmostEqual(gift_card_line.price_total, -100.0)
        self.assertAlmostEqual(order.amount_total, before_gift_card_payment - 100.0)
        self.assertTrue(all(line.tax_id for line in order.order_line))
        self.assertEqual(order.order_line.tax_id, self.tax_15pc_excl)

        # TAX INCL
        gift_card_line.unlink()  # Remove gift card
        self.program_gift_card.reward_ids.discount_line_product_id.taxes_id = [
            Command.set(self.tax_10pc_incl.ids)
        ]
        self._apply_promo_code(order, gift_card.code)
        gift_card_line = order.order_line - sol
        self.assertAlmostEqual(gift_card_line.price_total, -100.0)
        self.assertAlmostEqual(order.amount_total, before_gift_card_payment - 100.0)
        self.assertTrue(all(line.tax_id for line in order.order_line))
        self.assertEqual(gift_card_line.tax_id, self.tax_10pc_incl)

        # TAX INCL + TAX EXCL
        gift_card_line.unlink()  # Remove gift card
        self.program_gift_card.reward_ids.discount_line_product_id.taxes_id = [
            Command.link(self.tax_15pc_excl.id)
        ]
        self._apply_promo_code(order, gift_card.code)
        gift_card_line = order.order_line - sol
        self.assertAlmostEqual(gift_card_line.price_total, -100.0)
        self.assertAlmostEqual(order.amount_total, before_gift_card_payment - 100.0)
        self.assertTrue(all(line.tax_id for line in order.order_line))
        self.assertEqual(gift_card_line.tax_id, self.tax_10pc_incl + self.tax_15pc_excl)

    def test_paying_with_gift_card_fixed_tax(self):
        """ Test payment of sale order with fixed tax using gift card """
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()
        gift_card = self.program_gift_card.coupon_ids[0]

        tax_10_fixed = self.env['account.tax'].create({
            'name': "10$ Fixed tax",
            'amount_type': 'fixed',
            'amount': 10,
        })
        self.product_A.write({'list_price': 90})
        self.product_A.taxes_id = tax_10_fixed

        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': "Ordinary Product A",
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._apply_promo_code(order, gift_card.code)
        order.action_confirm()
        self.assertEqual(order.amount_total, 0, "The order should be totally paid")
