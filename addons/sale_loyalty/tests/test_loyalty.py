# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged, new_test_user
from odoo.tools.float_utils import float_compare

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


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

        cls.ewallet_program = cls.env['loyalty.program'].create({
            'name': 'eWallet Program',
            'program_type': 'ewallet',
            'trigger': 'auto',
            'applies_on': 'future',
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
            })],
            'rule_ids': [Command.create({
                'reward_point_amount': '1',
                'reward_point_mode': 'money',
                'product_ids': cls.env.ref('loyalty.ewallet_product_50'),
            })],
            'trigger_product_ids': cls.env.ref('loyalty.ewallet_product_50'),
        })

        cls.ewallet = cls.env['loyalty.card'].create({
            'program_id': cls.ewallet_program.id,
            'partner_id': cls.partner_a.id,
            'points': 10,
        })
        cls.ewallet_program.coupon_ids = [Command.set([cls.ewallet.id])]

        cls.user_salemanager = new_test_user(cls.env, login='user_salemanager', groups='sales_team.group_sale_manager')

        cls.promotion_code_10pc = cls.env['loyalty.program'].create({
            'name': "Code for 10% on orders",
            'trigger': 'with_code',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'mode': 'with_code',
                'code': 'test_10pc',
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })

    def test_nominative_programs(self):
        loyalty_program = self.env['loyalty.program'].create({
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
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        order._update_programs_and_rewards()
        claimable_rewards = order._get_claimable_rewards()
        # Should be empty since we do not have any coupon created yet
        self.assertFalse(claimable_rewards, "No program should be applicable")
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_a.id,
            'points': 10,
        })
        self.ewallet.points = 0

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
        self.ewallet.points = 50
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

    def test_points_awarded_global_discount_code_no_domain_program(self):
        """
        Check the calculation for points awarded when there is a global discount applied and the
        loyalty program applies on all products (no domain).
        """
        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])

        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_a.id,
            'points': 0,
        })

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_id': False,
                }),
            ]
        })

        promotion_program = self.env['loyalty.program'].create([{
            'name': "Coupon Program",
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                    'reward_point_amount': 1,
                    'reward_point_mode': 'order',
                    'minimum_amount': 10,
                })],
            'reward_ids': [Command.create({
                    'reward_type': 'discount',
                    'discount': 10.0,
                    'discount_applicability': 'order',
                    'required_points': 1,
                })],
        }])

        self.assertEqual(order.amount_total, 100)
        self._auto_rewards(order, promotion_program)
        self.assertEqual(order.amount_total, 90)
        order.action_confirm()
        self.assertEqual(loyalty_card.points, 90)

    def test_points_awarded_discount_code_no_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on all products (no domain).
        """
        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_a.id,
            'points': 0,
        })

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_id': False,
                }),
            ]
        })

        self.assertEqual(order.amount_total, 100)
        self._apply_promo_code(order, "test_10pc")
        self.assertEqual(order.amount_total, 90)
        order.action_confirm()
        self.assertEqual(loyalty_card.points, 90)

    def test_points_awarded_general_discount_code_specific_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on a specific domain. The discount code has no domain. The product
        related to that discount is not in the domain of the loyalty program.
        Expected behavior: The discount is not included in the computation of points
        """
        product_category_base = self.env.ref('product.product_category_1')
        product_category_food = self.env['product.category'].create({
            'name': "Food",
            'parent_id': product_category_base.id
        })

        self.product_A.categ_id = product_category_food
        self.product_B.list_price = 50

        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_program.rule_ids.product_category_id = product_category_food.id
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_a.id,
            'points': 0,
        })

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_id': False,
                }),
                Command.create({
                    'product_id': self.product_B.id,
                    'tax_id': False,
                }),
            ]
        })

        self.assertEqual(order.amount_total, 150)
        self._apply_promo_code(order, "test_10pc")
        self.assertEqual(order.amount_total, 135)  # (product_A + product_B) * 0.9
        order.action_confirm()
        self.assertEqual(loyalty_card.points, 100)

    def test_points_awarded_specific_discount_code_specific_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on a specific domain. The discount code has the same domain as the
        loyalty program. The product related to that discount code is set up to be included in the
        domain of the loyalty program.
        Expected behavior: The discount is included in the computation of points
        """
        product_category_base = self.env.ref('product.product_category_1')
        product_category_food = self.env['product.category'].create({
            'name': "Food",
            'parent_id': product_category_base.id
        })

        self.product_A.categ_id = product_category_food
        self.product_B.list_price = 50

        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_program.rule_ids.product_category_id = product_category_food.id
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_a.id,
            'points': 0,
        })

        self.promotion_code_10pc.rule_ids.product_category_id = product_category_food.id
        self.promotion_code_10pc.reward_ids.discount_applicability = 'specific'
        self.promotion_code_10pc.reward_ids.discount_product_category_id = product_category_food.id

        discount_product = self.env['product.product'].search([('id', '=', self.promotion_code_10pc.reward_ids.discount_line_product_id.id)])
        discount_product.categ_id = product_category_food.id

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_id': False,
                }),
                Command.create({
                    'product_id': self.product_B.id,
                    'tax_id': False,
                }),
            ]
        })

        self.assertEqual(order.amount_total, 150)
        self._apply_promo_code(order, "test_10pc")
        self.assertEqual(order.amount_total, 140)  # (product_A * 0.9 ) + product_B
        order.action_confirm()
        self.assertEqual(loyalty_card.points, 90)

    def test_points_awarded_ewallet(self):
        """
        Check the calculation for point awarded when using ewallet
        """
        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_a.id,
            'points': 0,
        })
        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_id': False,
                }),
            ]
        })

        self.assertEqual(order.amount_total, 100)
        order._update_programs_and_rewards()
        self._claim_reward(order, self.ewallet_program, coupon=self.ewallet)
        self.assertEqual(order.amount_total, 90)
        order.action_confirm()
        self.assertEqual(loyalty_card.points, 100)

    def test_points_awarded_giftcard(self):
        """
        Check the calculation for point awarded when using a gift card
        """
        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_a.id,
            'points': 0,
        })

        program_gift_card = self.env['loyalty.program'].create({
            'name': "Gift Cards",
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
            'points_granted': 50,
        }).generate_coupons()
        gift_card = program_gift_card.coupon_ids[0]

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'tax_id': False,
                }),
            ]
        })

        self.assertEqual(order.amount_total, 100)
        self._apply_promo_code(order, gift_card.code)
        self.assertEqual(order.amount_total, 50)
        order.action_confirm()
        self.assertEqual(loyalty_card.points, 100)

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

    def test_promotion_program_restricted_to_pricelists(self):
        self.env['product.pricelist'].search([]).action_archive()
        company_currency = self.env.company.currency_id
        pricelist_1, pricelist_2 = self.env['product.pricelist'].create([
            {'name': 'Basic company_currency pricelist', 'currency_id': company_currency.id},
            {'name': 'Other company_currency pricelist', 'currency_id': company_currency.id},
        ])
        self.immediate_promotion_program.active = True
        order = self.empty_order.copy()
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
        ]})

        applied_message = "The promo offer should have been applied."
        not_applied_message = "The promo offer should not have been applied because the order's " \
                              "pricelist is not eligible to this promotion."

        order.pricelist_id = self.env['product.pricelist']
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 3, applied_message)

        order.pricelist_id = pricelist_1
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 3, applied_message)

        self.immediate_promotion_program.pricelist_ids = [pricelist_1.id]
        order.pricelist_id = self.env['product.pricelist']
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 2, not_applied_message)

        order.pricelist_id = pricelist_1
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 3, applied_message)

        order.pricelist_id = pricelist_2
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 2, not_applied_message)

        self.immediate_promotion_program.pricelist_ids = [pricelist_1.id, pricelist_2.id]
        order.pricelist_id = self.env['product.pricelist']
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 2, not_applied_message)

        order.pricelist_id = pricelist_1
        order._update_programs_and_rewards()
        self._claim_reward(order, self.immediate_promotion_program)
        self.assertEqual(len(order.order_line.ids), 3, applied_message)

    def test_coupon_program_restricted_to_pricelists(self):
        self.env['product.pricelist'].search([]).action_archive()
        company_currency = self.env.company.currency_id
        pricelist_1, pricelist_2 = self.env['product.pricelist'].create([
            {'name': 'Basic company_currency pricelist', 'currency_id': company_currency.id},
            {'name': 'Other company_currency pricelist', 'currency_id': company_currency.id},
        ])

        self.code_promotion_program.active = True
        self.env['loyalty.generate.wizard'].with_context(
            active_id=self.code_promotion_program.id
        ).create({'coupon_qty': 7, 'points_granted': 1}).generate_coupons()
        coupons = self.code_promotion_program.coupon_ids

        order_no_pricelist = self.empty_order.copy()
        order_no_pricelist.write({'pricelist_id': None, 'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
        ]})
        order_pricelist_1 = order_no_pricelist.copy()
        order_pricelist_1.pricelist_id = pricelist_1
        order_pricelist_2 = order_no_pricelist.copy()
        order_pricelist_2.pricelist_id = pricelist_2

        applied_message = "The coupon code should have been applied."
        not_applied_message = "The coupon code should not have been applied because the order's " \
                              "pricelist is not eligible to this promotion."

        order_0 = order_no_pricelist.copy()
        self._apply_promo_code(order_0, coupons[0].code)
        self.assertEqual(len(order_0.order_line.ids), 2, applied_message)

        order_1 = order_pricelist_1.copy()
        self._apply_promo_code(order_1, coupons[1].code)
        self.assertEqual(len(order_1.order_line.ids), 2, applied_message)

        self.code_promotion_program.pricelist_ids = [pricelist_1.id]
        order_2 = order_no_pricelist.copy()
        with self.assertRaises(ValidationError):
            self._apply_promo_code(order_2, coupons[2].code)
        self.assertEqual(len(order_2.order_line.ids), 1, not_applied_message)

        order_3 = order_pricelist_1.copy()
        self._apply_promo_code(order_3, coupons[3].code)
        self.assertEqual(len(order_3.order_line.ids), 2, applied_message)

        order_4 = order_pricelist_2.copy()
        with self.assertRaises(ValidationError):
            self._apply_promo_code(order_4, coupons[4].code)
        self.assertEqual(len(order_4.order_line.ids), 1, not_applied_message)

        self.code_promotion_program.pricelist_ids = [pricelist_1.id, pricelist_2.id]
        order_5 = order_no_pricelist.copy()
        with self.assertRaises(ValidationError):
            self._apply_promo_code(order_5, coupons[5].code)
        self.assertEqual(len(order_5.order_line.ids), 1, not_applied_message)

        order_6 = order_pricelist_1.copy()
        self._apply_promo_code(order_6, coupons[6].code)
        self.assertEqual(len(order_6.order_line.ids), 2, applied_message)

    def test_specific_promotion_on_free_product(self):

        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [],
        })

        promotion_program = self.env['loyalty.program'].create([{
            'name': 'Promotion Program',
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
                'discount_product_ids': [product_A.id],
                'required_points': 1,
            })],
        }])

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': product_A.id,
                }),
                Command.create({
                    'product_id': product_A.id,
                    'discount': 100,
                }),
            ]
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, promotion_program)
        self.assertEqual(order.amount_total, 90)

    def test_gift_card_program_without_product(self):
        product_A = self.env['product.product'].create({
            'name': 'Product A',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [],
        })

        giftcard_program = self.env['loyalty.program'].create([{
            'name': 'Gift Card Program',
            'program_type': 'gift_card',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'reward_point_amount': 1,
                'reward_point_mode': 'unit',
            })],
        }])

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': product_A.id,
                }),
            ]
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, giftcard_program)

        self.assertEqual(giftcard_program.coupon_count, 0)

    def test_100_percent_discount(self):
        """
        Check whether a program offering 100% discount on an order reduces the order's total amount
        to zero.

        Assumes global tax rounding, as there's no good way to ensure the tax of the reward product
        equals the sum of taxes of the lines when each of them gets rounded.
        """
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        loyalty_program = self.env['loyalty.program'].create([{
            'name': 'Full Discount',
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
                'discount': 100,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        }])
        self.env['loyalty.card'].create({
            'program_id': loyalty_program.id, 'partner_id': self.partner_a.id, 'points': 2
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product_A.id, 'product_uom_qty': 1, 'price_unit': price
            }) for price in (5.60, 8.92, 44.91, 217.26, 2400.00)],
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, loyalty_program)
        msg = "100% discount on order should reduce total amount to 0"
        self.assertEqual(order.amount_total, 0, msg=msg)

    def test_discount_on_taxes_with_child_tax(self):
        """
        Check whether a program discount properly apply when product contain group of tax.
        """
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        loyalty_program = self.env['loyalty.program'].create([{
            'name': '90% Discount',
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
                'discount': 90,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        }])
        self.env['loyalty.card'].create({'program_id': loyalty_program.id, 'partner_id': self.partner_a.id, 'points': 2})
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {'product_id': self.product_D.id, 'product_uom_qty': 1})],
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, loyalty_program)
        msg = "Discountable should take child tax amount into account"
        self.assertEqual(order.amount_total, 10, msg=msg)

    def test_ewallet_program_without_trigger_product(self):
        self.ewallet_program.trigger_product_ids = [Command.clear()]
        self.ewallet.points = 1000

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'points_cost': 100,
                'product_uom_qty': 1,
            })],
        })
        order._update_programs_and_rewards()
        self._claim_reward(order, self.ewallet_program, coupon=self.ewallet)
        order.action_confirm()

        self.assertEqual(self.ewallet.points, 900)

    def test_ewallet_applied_ewallet_topup_in_order(self):
        self.ewallet.points = 10

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'points_cost': 100,
                'product_uom_qty': 1,
            }), Command.create({
                'product_id': self.env.ref('loyalty.ewallet_product_50').id,
                'product_uom_qty': 1,
            })],
        })
        order._update_programs_and_rewards()
        self._claim_reward(order, self.ewallet_program, coupon=self.ewallet)
        order.action_confirm()

        self.assertEqual(self.ewallet.points, 50)

    def test_archived_reward_products(self):
        """
        Check that we do not use loyalty rewards that have no active reward product.
        In the case where the reward is based on reward_product_tag_id we also check
        the case where at least one reward is  active.
        """

        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_program_tag = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])

        free_product_tag = self.env['product.tag'].create({'name': 'Free Product'})
        self.product_b.write({'product_tag_ids': [(4, free_product_tag.id)]})
        product_c = self.env['product.template'].create(
            {
                'name': 'Free Product C',
                'list_price': 1,
                'product_tag_ids': [(4, free_product_tag.id)],
            }
        )

        loyalty_program.reward_ids[0].write({
            'reward_type': 'product',
            'required_points': 1,
            'reward_product_id': self.product_b,
        })
        loyalty_program_tag.reward_ids[0].write({
            'reward_type': 'product',
            'required_points': 1,
            'reward_product_tag_id': free_product_tag.id,
        })
        self.product_b.active = False
        product_c.active = False

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                }),
            ]
        })

        order._update_programs_and_rewards()
        rewards = [value.ids for value in order._get_claimable_rewards().values()]
        self.assertTrue(all(loyalty_program.reward_ids[0].id not in r for r in rewards))
        self.assertTrue(all(loyalty_program_tag.reward_ids[0].id not in r for r in rewards))

        product_c.active = True
        order._update_programs_and_rewards()
        rewards = [value.ids for value in order._get_claimable_rewards().values()]
        self.assertTrue(any(loyalty_program_tag.reward_ids[0].id in r for r in rewards))

    def test_discount_reward_claimable_only_once(self):
        """
        Check that discount rewards already applied won't be shown in the claimable rewards anymore.
        """
        program = self.env['loyalty.program'].create({
            'name': '10% Discount',
            'applies_on': 'current',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'rule_ids': [(0, 0, {'mode': 'with_code', 'code': '10PERCENT'})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
            })],
        })

        coupon = self.env['loyalty.card'].create({
            'program_id': program.id, 'points': 20, 'code': 'GIFT_CARD'
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_a.id})]
        })

        self._claim_reward(order, program, coupon)
        rewards = order._get_claimable_rewards()
        self.assertFalse(rewards, "No program should be applicable")
