# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import common, Form


@common.tagged('post_install', '-at_install')
class TestLoyaltyDeliveryCost(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestLoyaltyDeliveryCost, cls).setUpClass()
        cls.SaleOrder = cls.env['sale.order']
        cls.partner_1 = cls.env['res.partner'].create({'name': 'My Test Customer'})
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })
        cls.product_4 = cls.env['product.product'].create({'name': 'A product to deliver'})
        cls.product_uom_unit = cls.env.ref('uom.product_uom_unit')

    def test_free_delivery_cost_with_ewallet(self):
        """
        Automatic free shipping of a delivery carrier should not be affected by the
        use of an ewallet when paying.
        Paying for an order of value 200 with an ewallet should still trigger the
        free shipping of the selected carrier if the free shipping is for amounts
        over 100.
        """

        # Create a delivery product and service.
        product_delivery_free = self.env['product.product'].create({
            'name': 'Test Delivery Product',
            'type': 'service',
            'list_price': 10.0,
            'categ_id': self.env.ref('delivery.product_category_deliveries').id,
        })
        free_delivery = self.env['delivery.carrier'].create({
            'name': 'Test Free Delivery',
            'product_id': product_delivery_free.id,
            'free_over': True,
            'amount': 100,
        })

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
            'points_granted': 1000,
        }).generate_coupons()
        reward_ewallet = program_ewallet.reward_ids[0]
        ewallet = program_ewallet.coupon_ids[0]

        # Create an order and pay with the ewallet.
        order = self.SaleOrder.create({
            'partner_id': self.partner_1.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [Command.create({
                'product_id': self.product_4.id,
                'price_unit': 200.00,
            })]
        })
        order._apply_program_reward(reward_ewallet, ewallet)
        order.action_confirm()

        # Ask for delivery, delivery cost should not take into account the ewallet when computing
        # the amount of the sale order.
        delivery_wizard = self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id,
            'default_carrier_id': free_delivery.id,
        })
        delivery_wizard.button_confirm()

        self.assertEqual(order.amount_untaxed, 200.0, "Delivery cost is not added.")

    def test_delivery_cost_gift_card(self):
        """
        A customer has a carrier with the amount greater than the one to have
        free shipping cost, then uses a gift card that lowers that amount to less
        than the threshold: the shipping cost should still be 0.0
        """

        product_delivery_free = self.env['product.product'].create({
            'name': 'Free Delivery Charges',
            'type': 'service',
            'list_price': 40.0,
            'categ_id': self.env.ref('delivery.product_category_deliveries').id,
        })
        free_delivery = self.env['delivery.carrier'].create({
            'name': 'Delivery Now Free Over 100',
            'fixed_price': 40,
            'delivery_type': 'fixed',
            'product_id': product_delivery_free.id,
            'free_over': True,
            'amount': 100,
        })
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
            'points_granted': 40,
        }).generate_coupons()
        gift_card = program_gift_card.coupon_ids[0]


        sale_normal_delivery_charges = self.SaleOrder.create({
            'partner_id': self.partner_1.id,
            'partner_invoice_id': self.partner_1.id,
            'partner_shipping_id': self.partner_1.id,
            'pricelist_id': self.pricelist.id,
            'order_line': [(0, 0, {
                'name': 'PC Assamble + 2GB RAM',
                'product_id': self.product_4.id,
                'product_uom_qty': 1,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 120.00,
            })]
        })
        self._apply_promo_code(sale_normal_delivery_charges, gift_card.code)
        sale_normal_delivery_charges.action_confirm()

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_normal_delivery_charges.id,
            'default_carrier_id': free_delivery.id,
        }))
        delivery_wizard.save().button_confirm()

        self.assertEqual(len(sale_normal_delivery_charges.order_line), 3)
        self.assertEqual(sale_normal_delivery_charges.amount_untaxed, 80.0, "Delivery cost is not Added")

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
