# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import common, Form

@common.tagged('post_install', '-at_install')
class TestLoyaltyDeliveryCost(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SaleOrder = cls.env['sale.order']
        cls.partner_1 = cls.env['res.partner'].create({'name': 'My Test Customer'})
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })
        cls.product_4 = cls.env['product.product'].create({'name': 'A product to deliver'})
        cls.product_uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product_delivery = cls.env['product.product'].create({
            'name': 'Delivery Charges',
            'type': 'service',
            'list_price': 40.0,
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
        })
        cls.delivery_carrier = cls.env['delivery.carrier'].create({
            'name': 'Delivery Now Free Over 100',
            'fixed_price': 40,
            'delivery_type': 'fixed',
            'product_id': cls.product_delivery.id,
            'free_over': True,
            'amount': 100,
        })

    def test_delivery_cost_gift_card(self):
        """
        Test that the order amount used to trigger the free delivery doesn't consider gift cards.
        """

        program_gift_card = self.env['loyalty.program'].create({
            'name': 'Gift Cards',
            'applies_on': 'future',
            'program_type': 'gift_card',
            'trigger': 'auto',
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 1,
                'discount_mode': 'per_point',
                'discount_applicability': 'order',
            })]
        })
        self.env['loyalty.generate.wizard'].with_context(active_id=program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 200,
        }).generate_coupons()
        gift_card = program_gift_card.coupon_ids[0]

        order = self.SaleOrder.create({
            'partner_id': self.partner_1.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [Command.create({'product_id': self.product_4.id, 'price_unit': 200.00})]
        })
        self._apply_promo_code(order, gift_card.code)
        order.action_confirm()

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id, 'default_carrier_id': self.delivery_carrier.id,
        }))
        delivery_wizard.save().button_confirm()

        self.assertEqual(order.order_line.filtered('is_delivery').price_total, 0)

    def test_free_delivery_cost_with_ewallet(self):
        """
        Automatic free shipping of a delivery carrier should not be affected by the
        use of an ewallet when paying.
        Paying for an order of value 200 with an ewallet should still trigger the
        free shipping of the selected carrier if the free shipping is for amounts
        over 100.
        """

        # Create an eWallet Program and its corresponding rewards and coupons.
        program_ewallet = self.env['loyalty.program'].create({
            'name': 'eWallet',
            'program_type': 'ewallet',
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        self.env['loyalty.generate.wizard'].with_context(active_id=program_ewallet.id).create({
            'coupon_qty': 1,
            'points_granted': 200,
        }).generate_coupons()
        reward_ewallet = program_ewallet.reward_ids[0]
        ewallet = program_ewallet.coupon_ids[0]

        # Create an order and pay with the ewallet.
        order = self.SaleOrder.create({
            'partner_id': self.partner_1.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [Command.create({'product_id': self.product_4.id, 'price_unit': 200.00})]
        })
        order._apply_program_reward(reward_ewallet, ewallet)

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id, 'default_carrier_id': self.delivery_carrier.id,
        }))
        delivery_wizard.save().button_confirm()

        self.assertEqual(order.order_line.filtered('is_delivery').price_total, 0)

    def test_delivery_cost_discounts(self):
        """
            make sure discounts aren't taken into account for free delivery
        """
        discount90 = self.env['loyalty.program'].create({
            'name': '90% Discount',
            'program_type': 'coupons',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 90,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })]
        })

        # Create an order and apply discount.
        order = self.SaleOrder.create({
            'partner_id': self.partner_1.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [Command.create({'product_id': self.product_4.id, 'price_unit': 200.00,})]
        })
        order._update_programs_and_rewards()
        coupon = order.coupon_point_ids.coupon_id.filtered(lambda c: c.program_id == discount90)
        order._apply_program_reward(discount90.reward_ids, coupon)
        order.action_confirm()

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id, 'default_carrier_id': self.delivery_carrier.id,
            }))
        delivery_wizard.save().button_confirm()

        self.assertEqual(
            order.order_line.filtered('is_delivery').price_unit,
            self.product_delivery.list_price
        )

    def _apply_promo_code(self, order, code, no_reward_fail=True):
        status = order._try_apply_code(code)
        if 'error' in status:
            raise ValidationError(status['error'])
        if not status and no_reward_fail:
            # Can happen if global discount got filtered out in `_get_claimable_rewards`
            raise ValidationError('No reward to claim with this coupon')
        coupons = self.env['loyalty.card']
        rewards = self.env['loyalty.reward']
        for coupon, coupon_rewards in status.items():
            coupons |= coupon
            rewards |= coupon_rewards
        if len(coupons) == 1 and len(rewards) == 1:
            status = order._apply_program_reward(rewards, coupons)
            if 'error' in status:
                raise ValidationError(status['error'])
