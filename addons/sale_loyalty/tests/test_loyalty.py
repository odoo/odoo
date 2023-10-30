# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, new_test_user
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.tools.float_utils import float_compare
from odoo import Command

@tagged('post_install', '-at_install')
class TestLoyalty(TestSaleCouponCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['loyalty.program'].search([]).write({'active': False})

        cls.partner_a = cls.env['res.partner'].create({'name': 'Jean Jacques'})

        cls.product_a = cls.env['product.product'].create({
            'name': 'Product C',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [(6, 0, [])],
        })

        cls.user_salemanager = new_test_user(cls.env, login='user_salemanager', groups='sales_team.group_sale_manager')

    def test_nominative_programs(self):
        loyalty_program, ewallet_program = self.env['loyalty.program'].create([
            {
                'name': 'Loyalty Program',
                'program_type': 'loyalty',
                'trigger': 'auto',
                'applies_on': 'both',
                'rule_ids': [(0, 0, {
                    'reward_point_mode': 'unit',
                    'reward_point_amount': 1,
                    'product_ids': [self.product_a.id],
                })],
                'reward_ids': [(0, 0, {
                    'reward_type': 'discount',
                    'discount': 1.5,
                    'discount_mode': 'per_point',
                    'discount_applicability': 'order',
                    'required_points': 3,
                })],
            },
            {
                'name': 'eWallet Program',
                'program_type': 'ewallet',
                'applies_on': 'future',
                'trigger': 'auto',
                'rule_ids': [(0, 0, {
                    'reward_point_mode': 'money',
                    'reward_point_amount': 10,
                })],
                'reward_ids': [(0, 0, {})],
            }
        ])

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        order._update_programs_and_rewards()
        claimable_rewards = order._get_claimable_rewards()
        # Should be empty since we do not have any coupon created yet
        self.assertFalse(claimable_rewards, "No program should be applicable")
        loyalty_card, ewallet_coupon = self.env['loyalty.card'].create([
            {
                'program_id': loyalty_program.id,
                'partner_id': self.partner_a.id,
                'points': 10,
            },
            {
                'program_id': ewallet_program.id,
                'partner_id': self.partner_a.id,
                'points': 0,
            },
        ])
        order.write({
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
            })]
        })
        order._update_programs_and_rewards()
        claimable_rewards = order._get_claimable_rewards()
        self.assertEqual(len(claimable_rewards), 1, "The ewallet program should not be applicable since the card has no points.")
        vals = order._get_reward_values_discount(loyalty_program.reward_ids[0], loyalty_card)
        self.assertEqual(
            vals[0]['points_cost'] % loyalty_program.reward_ids.required_points,
            0,
            "Can only use a whole number of required points",
        )
        self.assertEqual(vals[0]['points_cost'], 9, "Use maximum available points for the reward")
        ewallet_coupon.points = 50
        order._update_programs_and_rewards()
        claimable_rewards = order._get_claimable_rewards()
        self.assertEqual(len(claimable_rewards), 2, "Now that the ewallet has some points they should both be applicable.")

    def test_cancel_order_with_coupons(self):
        """This test ensure that creating an order with coupons will not
        raise an access error on POS line modele when canceling the order."""

        self.env['loyalty.program'].create({
            'name': '10% Discount',
            'program_type': 'coupons',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })]
        })

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_a.id,
                })
            ]
        })

        order._update_programs_and_rewards()
        self.assertTrue(order.coupon_point_ids)

        # Canceling the order should not raise an access error:
        # During the cancel process, we are trying to get `use_count` of the coupon,
        # and we call the `_compute_use_count` that is also in pos_loyalty.
        # This last one will try to find related POS lines while user have not access to POS.
        order._action_cancel()
        self.assertFalse(order.coupon_point_ids)

    def test_distribution_amount_payment_programs(self):
        """
        Check how the amount of a payment reward is distributed.
        An ewallet should not be used to refund taxes.
        Its amount must be distributed between the products.
        """

        # Create two products
        product_a, product_b = self.env['product.product'].create([
            {
                'name': 'Product A',
                'list_price': 100,
                'sale_ok': True,
                'taxes_id': [Command.set(self.tax_15pc_excl.ids)],
            },
            {
                'name': 'Product B',
                'list_price': 100,
                'sale_ok': True,
                'taxes_id': [Command.set(self.tax_15pc_excl.ids)],
            },
        ])

        # Create a coupon and a ewallet
        coupon_program, ewallet_program = self.env['loyalty.program'].create([
            {
                'name': 'Coupon Program',
                'program_type': 'coupons',
                'trigger': 'with_code',
                'applies_on': 'both',
                'reward_ids': [Command.create({
                        'reward_type': 'discount',
                        'discount': 100.0,
                        'discount_applicability': 'specific',
                        'discount_product_domain': '[("name", "=", "Product A")]',
                })],
            },
            {
                'name': 'eWallet Program',
                'program_type': 'ewallet',
                'applies_on': 'future',
                'trigger': 'auto',
                'rule_ids': [Command.create({
                    'reward_point_mode': 'money',
                })],
                'reward_ids': [Command.create({
                    'discount_mode': 'per_point',
                    'discount': 1,
                    'discount_applicability': 'order',
                })],
            }
        ])

        coupon_partner, _ = self.env['loyalty.card'].create([
            {
                'program_id': coupon_program.id,
                'partner_id': self.partner_a.id,
                'points': 1,
                'code': '5555',
            },
            {
                'program_id': ewallet_program.id,
                'partner_id': self.partner_a.id,
                'points': 115,
            },
        ])

        # Create the order
        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                    Command.create({
                        'product_id': product_a.id,
                    }),
                    Command.create({
                        'product_id': product_b.id,
                    }),
            ]
        })

        self.assertEqual(order.amount_total, 230.0)
        self.assertEqual(order.amount_untaxed, 200.0)
        self.assertEqual(order.amount_tax, 30.0)

        # Apply the eWallet
        order._update_programs_and_rewards()
        self._claim_reward(order, ewallet_program)

        self.assertEqual(order.amount_total, 115.0)
        self.assertEqual(order.amount_untaxed, 85.0)
        self.assertEqual(order.amount_tax, 30.0)
        self.assertEqual(order.reward_amount, -115.0)

        # Apply the coupon
        self._apply_promo_code(order, coupon_partner.code)

        self.assertEqual(order.amount_total, 0.0)
        self.assertEqual(order.amount_untaxed, -15.0)
        self.assertEqual(order.amount_tax, 15.0)
        self.assertEqual(order.reward_amount, -215.0)

    def test_discount_max_amount_on_specific_product(self):
        product_a = self.product_A
        product_b = self.product_B
        product_a.write({'taxes_id': [Command.set(self.tax_20pc_excl.ids)]})
        product_b.write({'list_price': -20, 'taxes_id': [Command.set(self.tax_20pc_excl.ids)]})

        self.env['loyalty.program'].search([]).write({'active': False})
        promotion = self.env['loyalty.program'].create({
            'name': '10% Discount',
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': 1, 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'discount': 10.0,
                'discount_max_amount': 9,
                'discount_applicability': 'specific',
                'discount_product_ids': [product_a.id],
            })],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': product_a.id})],
        })
        self.assertEqual(order.reward_amount, 0)

        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "Max discount amount reached, the reward amount should be the max amount value."
        self.assertEqual(reward_amount_tax_included, -9, msg)

        order.order_line = [Command.clear(), Command.create({'product_id': product_b.id})]
        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "This product is not eligible to the discount."
        self.assertEqual(reward_amount_tax_included, 0, msg=msg)

        order.order_line = [
            Command.clear(),
            Command.create({'product_id': product_a.id}),  # price_total = 120
            Command.create({'product_id': product_b.id}),  # price_total = -20
        ]
        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "Reward amount above the max amount, the reward should be the max amount value."
        self.assertEqual(reward_amount_tax_included, -9, msg)

        order.order_line = [
            Command.clear(),
            Command.create({'product_id': product_a.id}),                     # price_total = 120
            Command.create({'product_id': product_b.id, 'price_unit': -95}),  # price_total = -114
        ]
        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "Reward amount should never surpass the order's current total amount."
        self.assertEqual(reward_amount_tax_included, -6, msg)

        order.order_line = [
            Command.clear(),
            Command.create({'product_id': product_a.id, 'price_unit': 50}),  # price_total = 60
            Command.create({'product_id': product_b.id, 'price_unit': -5}),  # price_total = -6
        ]
        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "Reward amount should be the percentage one if under the max amount discount."
        self.assertEqual(reward_amount_tax_included, -6, msg)

    def test_multiple_discount_specific(self):
        """
        Check the discount calculation if it is based on the remaining amount
        """

        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [],
        })

        coupon_program = self.env['loyalty.program'].create([{
            'name': 'Coupon Program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                    'reward_point_amount': 1,
                    'reward_point_mode': 'unit',
                })],
            'reward_ids': [Command.create({
                    'reward_type': 'discount',
                    'discount': 10.0,
                    'discount_applicability': 'specific',
                    'required_points': 1,
                })],
        }])

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                    'product_id': product_A.id,
                    'product_uom_qty': 3,
                })]
        })

        self.assertEqual(float_compare(order.amount_total, 300, precision_rounding=3), 0)

        order._update_programs_and_rewards()
        self._claim_reward(order, coupon_program)
        self.assertEqual(float_compare(order.amount_total, 270, precision_rounding=3), 0, "300 * 0.9 = 270")

        order._update_programs_and_rewards()
        self._claim_reward(order, coupon_program)
        self.assertEqual(float_compare(order.amount_total, 243, precision_rounding=3), 0, "300 * 0.9 * 0.9 = 243")

        order._update_programs_and_rewards()
        self._claim_reward(order, coupon_program)
        self.assertEqual(float_compare(order.amount_total, 218.7, precision_rounding=3), 0, "300 * 0.9 * 0.9 * 0.9 = 218.7")
