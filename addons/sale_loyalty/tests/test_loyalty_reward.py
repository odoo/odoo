# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools.float_utils import float_compare

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('post_install', '-at_install')
class TestLoyaltyRewards(TestSaleCouponCommon):

    # === PRODUCT REWARDS TESTS === #

    def test_archived_reward_products(self):
        """ Ensure we do not use loyalty rewards that have no active reward product.

        When the reward is based on reward_product_tag_id, ensure at least one reward is active.
        """
        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_program_tag = LoyaltyProgram.create(
            LoyaltyProgram._get_template_values()['loyalty']
        )

        free_product_tag = self.env['product.tag'].create({'name': "Free Product"})
        self.product_B.write({'product_tag_ids': [(4, free_product_tag.id)]})
        product_c = self.env['product.template'].create({
            'name': "Free Product C",
            'list_price': 1,
            'product_tag_ids': [(4, free_product_tag.id)],
        })

        loyalty_program.reward_ids[0].write({
            'reward_type': 'product',
            'required_points': 1,
            'reward_product_id': self.product_B,
        })
        loyalty_program_tag.reward_ids[0].write({
            'reward_type': 'product',
            'required_points': 1,
            'reward_product_tag_id': free_product_tag.id,
        })
        self.product_B.active = False
        product_c.active = False

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product_A.id})]
        })

        order._update_programs_and_rewards()
        rewards = [value.ids for value in order._get_claimable_rewards().values()]
        self.assertTrue(all(loyalty_program.reward_ids[0].id not in r for r in rewards))
        self.assertTrue(all(loyalty_program_tag.reward_ids[0].id not in r for r in rewards))

        product_c.active = True
        order._update_programs_and_rewards()
        rewards = [value.ids for value in order._get_claimable_rewards().values()]
        self.assertTrue(any(loyalty_program_tag.reward_ids[0].id in r for r in rewards))

    # === DISCOUNT REWARDS (GENERIC) TESTS === #

    def test_reward_discount_on_taxes_with_child_tax(self):
        """ Ensure a program discount is properly apply when product contain group of taxes. """

        self.env.company.tax_calculation_rounding_method = 'round_globally'
        loyalty_program = self.env['loyalty.program'].create([{
            'name': "90% Discount",
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'reward_point_mode': 'unit',
                'reward_point_amount': 1,
                'product_ids': [self.product_A.id],
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 90,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        }])
        self.env['loyalty.card'].create({
            'program_id': loyalty_program.id, 'partner_id': self.partner.id, 'points': 2
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product_D.id, 'product_uom_qty': 1})],
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, loyalty_program)
        msg = "Discountable should take child tax amount into account"
        self.assertEqual(order.amount_total, 10, msg=msg)

    def test_reward_discount_claimable_only_once(self):
        """
        Check that discount rewards already applied won't be shown in the claimable rewards anymore.
        """
        program = self.env['loyalty.program'].create({
            'name': "10% Discount & Gift",
            'applies_on': 'current',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'rule_ids': [Command.create({'mode': 'with_code', 'code': "10PERCENT&GIFT"})],
            'reward_ids': [
                Command.create({
                    'reward_type': 'product',
                    'reward_product_id': self.product_B.id,
                    'reward_product_qty': 1,
                }),
                Command.create({
                    'reward_type': 'discount',
                    'discount': 10,
                    'discount_mode': 'percent',
                    'discount_applicability': 'specific',
                }),
            ],
        })

        coupon = self.env['loyalty.card'].create({
            'program_id': program.id, 'points': 20, 'code': 'GIFT_CARD'
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product_A.id})]
        })

        product_reward = program.reward_ids.filtered(lambda reward: reward.reward_type == 'product')
        discount_reward = program.reward_ids - product_reward
        order._apply_program_reward(discount_reward, coupon)
        rewards = order._get_claimable_rewards()[coupon]
        msg = "Only the free product should be applicable, as the discount was already applied."
        self.assertEqual(rewards, product_reward, msg)

    # === DISCOUNT REWARDS (ON ORDER) TESTS === #
    # TODO edm: add test for no linked discount lines

    def test_reward_100_percent_discount_on_order(self):
        """
        Check whether a program offering 100% discount on an order reduces the order's total amount
        to zero.

        Assumes global tax rounding, as there's no good way to ensure the tax of the reward product
        equals the sum of taxes of the lines when each of them gets rounded.
        """
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        loyalty_program = self.env['loyalty.program'].create([{
            'name': "Full Discount",
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [Command.create({
                'reward_point_mode': 'unit',
                'reward_point_amount': 1,
                'product_ids': [self.product_A.id],
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 100,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        }])
        self.env['loyalty.card'].create({
            'program_id': loyalty_program.id, 'partner_id': self.partner.id, 'points': 2
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product_A.id, 'product_uom_qty': 1, 'price_unit': price
            }) for price in (5.60, 8.92, 44.91, 217.26, 2400.00)],
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, loyalty_program)
        msg = "100% discount on order should reduce total amount to 0"
        self.assertEqual(order.amount_total, 0, msg=msg)

    # === DISCOUNT REWARDS (ON CHEAPEST) TESTS === #
    # TODO edm: add test and code for linked discount lines

    def test_reward_cheapest_product_applied_multiple_times(self):
        """ Check the application of a reward on the cheapest product. """

        self.env['loyalty.program'].search([]).action_archive()

        promotion = self.env['loyalty.program'].create({
            'name': "Second cheapest at 50%",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'discount': 50,
                'discount_applicability': 'cheapest',
                'clear_wallet': False,
            })],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'product_uom_qty': 1,
                    'price_unit': 100,  # price_total tax included: 115 (15% tax)
                }),
                Command.create({
                    'product_id': self.product_B.id,
                    'product_uom_qty': 1,
                    'price_unit': 15,  # price_total tax included: 17.25 (15% tax)
                }),
                Command.create({
                    'product_id': self.product_C.id,
                    'product_uom_qty': 3,
                    'price_unit': 333,  # price_total tax included: 333 (No tax)
                }),
            ]
        })

        msg = (
            f"Total amount should be 1131.25 (1*100*1.15 + 1*15*1.15 + 3*333) and not"
            f" {order.amount_total}."
        )
        self.assertEqual(float_compare(order.amount_total, 1131.25, precision_rounding=3), 0, msg)

        order._update_programs_and_rewards()
        self._claim_reward(order, program=promotion)

        self.assertEqual(len(order.order_line), 5, msg="2 discount lines should have been created.")
        no_tax_disc_line = order.order_line.filtered(lambda l: l.is_reward_line and not l.tax_ids)
        msg = (
            f"One line shouldn't have any tax, it's amount should be -166.5 (333*0.5) and not"
            f" {no_tax_disc_line.price_total}"
        )
        self.assertEqual(
            float_compare(no_tax_disc_line.price_total, -166.5, precision_rounding=3), 0, msg=msg
        )
        with_tax_discount_line = order.order_line.filtered(lambda l: l.is_reward_line and l.tax_ids)
        msg = (
            f"One line should have a 15% tax, it's amount should be ≃ -57.50 (100*1.15*0.5) and not"
            f" {with_tax_discount_line.price_total}."
        )
        self.assertEqual(float_compare(
            with_tax_discount_line.price_total, -57.50, precision_rounding=3
        ), 0, msg=msg)
        msg = (
            f"Total amount should be 907.25 (previous total - 100*1.15*0.5 - 333*0.5 discounted)"
            f" and not {order.amount_total}."
        )
        self.assertEqual(float_compare(order.amount_total, 907.25, precision_rounding=3), 0, msg)

    def test_reward_cheapest_product_applied_once_when_clear_wallet(self):
        """ Check the application of a reward on the cheapest product when clear wallet is set. """

        self.env['loyalty.program'].search([]).action_archive()

        promotion = self.env['loyalty.program'].create({
            'name': "Cheapest at 50%",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'discount': 50,
                'discount_applicability': 'cheapest',
                'clear_wallet': True,
            })],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'product_uom_qty': 1,
                    'price_unit': 100,  # price_total tax included: 115 (15% tax)
                }),
                Command.create({
                    'product_id': self.product_B.id,
                    'product_uom_qty': 1,
                    'price_unit': 15,  # price_total tax included: 17.25 (15% tax)
                }),
                Command.create({
                    'product_id': self.product_C.id,
                    'product_uom_qty': 3,
                    'price_unit': 333,  # price_total tax included: 333 (No tax)
                }),
            ]
        })

        msg = (
            f"Total amount should be 1131.25 (1*100*1.15 + 1*15*1.15 + 3*333) and not"
            f" {order.amount_total}."
        )
        self.assertEqual(float_compare(order.amount_total, 1131.25, precision_rounding=3), 0, msg)

        order._update_programs_and_rewards()
        self._claim_reward(order, program=promotion)

        msg = (
            f"Total amount should be 964.75 (previous total - 333*0.5 discounted) and not"
            f" {order.amount_total}."
        )
        self.assertEqual(float_compare(order.amount_total, 964.75, precision_rounding=3), 0, msg)

    def test_domain_on_cheapest_reward(self):
        product_tag = self.env['product.tag'].create({'name': "Discountable"})
        self.env['loyalty.program'].create({
            'name': "10% Discount",
            'program_type': 'promo_code',
            'rule_ids': [Command.create({'code': "10discount"})],
            'reward_ids': [
                Command.create({
                    'reward_type': 'discount',
                    'discount': 10,
                    'discount_mode': 'percent',
                    'discount_applicability': 'cheapest',
                    'discount_product_tag_id': product_tag.id,
                }),
            ],
        })
        self.product_A.product_tag_ids = product_tag
        order = self.empty_order
        order.write({
            'order_line': [
                # product_A: lst_price: 100, Tax included price: 115
                Command.create({'product_id': self.product_A.id}),
                # Product_B: lst_price: 5, Tax included price: 5.75
                Command.create({'product_id': self.product_B.id}),
            ]
        })

        with self.assertRaises(UserError, msg="There is nothing to discount"):
            # Try to discount the second cheapest among product with the tag when only 1
            self._apply_promo_code(order, '10discount')

        order.order_line[0].product_uom_qty = 2
        self._apply_promo_code(order, '10discount')
        msg = "Discount should only be applied to the line with a correctly tagged product."
        self.assertEqual(order.order_line[2].price_total, -11.5, msg)

        self.product_C.write({
            'list_price': 50,
            'product_tag_ids': product_tag,
        })
        order.order_line[2:].unlink()
        order.order_line[0].product_uom_qty = 1
        order.write({
            'order_line': [
                # product_C: lst_price = Tax included price: 50
                Command.create({'product_id': self.product_C.id}),
            ]
        })
        self._apply_promo_code(order, '10discount')
        msg = "Discount should be applied to the line with the cheapest valid product."
        self.assertEqual(order.order_line[3].price_total, -5.0, msg)

    # === DISCOUNT REWARDS (ON SPECIFIC) TESTS === #
    # TODO edm: add test and code for linked discount lines

    def test_discount_max_amount_on_specific_product(self):
        self.product_A.write({'taxes_id': [Command.set(self.tax_20pc_excl.ids)]})
        self.product_B.write({'list_price': -20, 'taxes_id': [Command.set(self.tax_20pc_excl.ids)]})

        self.env['loyalty.program'].search([]).write({'active': False})
        promotion = self.env['loyalty.program'].create({
            'name': "10% Discount",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': 1, 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'discount': 10.0,
                'discount_max_amount': 9,
                'discount_applicability': 'specific',
                'discount_product_ids': [self.product_A.id],
            })],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product_A.id})],
        })
        self.assertEqual(order.reward_amount, 0)

        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "Max discount amount reached, the reward amount should be the max amount value."
        self.assertEqual(reward_amount_tax_included, -9, msg)

        order.order_line = [Command.clear(), Command.create({'product_id': self.product_B.id})]
        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "This product is not eligible to the discount."
        self.assertEqual(reward_amount_tax_included, 0, msg=msg)

        order.order_line = [
            Command.clear(),
            Command.create({'product_id': self.product_A.id}),  # price_total = 120
            Command.create({'product_id': self.product_B.id}),  # price_total = -20
        ]
        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "Reward amount above the max amount, the reward should be the max amount value."
        self.assertEqual(reward_amount_tax_included, -9, msg)

        order.order_line = [
            Command.clear(),
            Command.create({'product_id': self.product_A.id}),                     # total = 120
            Command.create({'product_id': self.product_B.id, 'price_unit': -95}),  # total = -114
        ]
        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "Reward amount should never surpass the order's current total amount."
        self.assertEqual(reward_amount_tax_included, -6, msg)

        order.order_line = [
            Command.clear(),
            Command.create({'product_id': self.product_A.id, 'price_unit': 50}),  # price_total = 60
            Command.create({'product_id': self.product_B.id, 'price_unit': -5}),  # price_total = -6
        ]
        self._auto_rewards(order, promotion)
        reward_amount_tax_included = sum(l.price_total for l in order.order_line if l.reward_id)
        msg = "Reward amount should be the percentage one if under the max amount discount."
        self.assertEqual(reward_amount_tax_included, -6, msg)

    def test_reward_discount_specific_applied_multiple_times(self):
        """ Check the discount calculation if it is based on the remaining amount. """
        coupon_program = self.env['loyalty.program'].create([{
            'name': "Coupon Program",
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
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product_A.id,  # 100 + 15% tax
                'product_uom_qty': 3,
            })]
        })

        self.assertEqual(float_compare(order.amount_total, 345, precision_rounding=3), 0)

        order._update_programs_and_rewards()
        self._claim_reward(order, coupon_program)
        self.assertEqual(
            float_compare(order.amount_total, 310.5, precision_rounding=3), 0, "345 * 0.9 = 270"
        )

        order._update_programs_and_rewards()
        self._claim_reward(order, coupon_program)
        self.assertEqual(
            float_compare(order.amount_total, 279.45, precision_rounding=3),
            0,
            "345 * 0.9 * 0.9 = 279.45"
        )

        order._update_programs_and_rewards()
        self._claim_reward(order, coupon_program)
        self.assertEqual(
            float_compare(order.amount_total, 251.5, precision_rounding=3),
            0,
            "345 * 0.9 * 0.9 * 0.9 = 251.5"
        )

    def test_reward_discount_specific_on_free_product(self):
        promotion_program = self.env['loyalty.program'].create([{
            'name': "Promotion Program",
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
                'discount_product_ids': [self.product_A.id],
                'required_points': 1,
            })],
        }])

        order = self.env['sale.order'].with_user(self.user_salemanager).create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({'product_id': self.product_A.id}),  # 100 + 15% tax
                Command.create({'product_id': self.product_A.id, 'discount': 100}),
            ]
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, promotion_program)
        self.assertEqual(order.amount_total, 103.5)  # 115*.9

    # === FIXED PRICE REWARDS TESTS === #

    def test_reward_fixed_price_applies_on_selected_products_only(self):
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "all at 2 among selection",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed',
                'fixed_amount_per_unit': 2,
                'required_points': 3,
                'discount_product_ids': [self.product_A.id, self.product_C.id,],
            })],
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({'product_id': self.product_A.id}),  # 100 + 15% tax
                Command.create({'product_id': self.product_B.id}),  # 5 + 15% tax
                Command.create({'product_id': self.product_C.id}),  # 100 no tax
            ]
        })

        self.assertAlmostEqual(order.amount_total, 220.75)

        order._update_programs_and_rewards()
        self._claim_reward(order, promotion_program)

        discount_lines = order.order_line.filtered(lambda l: l.is_reward_line)
        discounted_lines = order.order_line.filtered(lambda l: l.discount_line_ids)
        self.assertEqual(len(discount_lines), 2, "2 discount lines should have been created.")
        self.assertEqual(len(discounted_lines), 2, "2 order lines should have been discounted.")
        msg = ("2 products with different taxes must lead to 2 discount lines, one per tax, each"
               " linked to the order line they were computed from.")
        self.assertTrue(all(dl in discounted_lines.discount_line_ids for dl in discount_lines), msg)
        self.assertEqual(len(discount_lines[0].discounted_line_ids), 1, msg=msg)
        self.assertEqual(len(discount_lines[1].discounted_line_ids), 1, msg=msg)
        self.assertTrue(
            discount_lines[0].discounted_line_ids != discount_lines[1].discounted_line_ids, msg=msg
        )
        for dl in discount_lines:
            self.assertEqual(dl.tax_ids, dl.discounted_line_ids.tax_ids, msg=msg)
            self.assertAlmostEqual(abs(dl.price_subtotal), dl.discounted_line_ids.price_subtotal - 2)
        self.assertFalse(
            order.order_line[1].discount_line_ids,
            "Only the products covered by the reward should have been discounted."
        )
        self.assertAlmostEqual(order.amount_total, 10.05)  # 2*1.15 (discounted) + 5*1.15 + 2 (discounted)

    def test_reward_fixed_price_applies_on_more_than_minimum_quantity_products(self):
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "all at 5 among selection",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed',
                'fixed_amount_per_unit': 5,
                'required_points': 3,
            })],
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product_A.id, 'product_uom_qty': 4  # 100 + 15% tax
            })],
        })

        self.assertAlmostEqual(order.amount_total, 460)

        order._update_programs_and_rewards()
        self._claim_reward(order, promotion_program)

        discount_line = order.order_line.filtered(lambda l: l.is_reward_line)
        expected_discount = -(discount_line.discounted_line_ids.price_subtotal - 20)
        msg = "All products should have been discounted."
        self.assertAlmostEqual(discount_line.price_subtotal, expected_discount, msg=msg)
        self.assertAlmostEqual(order.amount_total, 23, msg=msg)

    def test_reward_fixed_price_ignores_cheaper_than_promo_product(self):
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "all at 50",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed', 'fixed_amount_per_unit': 50, 'required_points': 3
            })],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({'product_id': self.product_A.id}),  # 100 + 15% tax
                Command.create({'product_id': self.product_B.id}),  # 5 + 15% tax
                Command.create({'product_id': self.product_C.id}),  # 100 no tax
            ]
        })

        self.assertAlmostEqual(order.amount_total, 220.75)
        self.assertTrue(order.order_line[0].tax_ids)
        self.assertTrue(order.order_line[1].tax_ids)
        self.assertFalse(order.order_line[2].tax_ids)

        order._update_programs_and_rewards()
        self._claim_reward(order, promotion_program)

        discount_lines = order.order_line.filtered(lambda l: l.is_reward_line)
        msg = "2 discount lines should have been created, one for the 15% tax, and one without tax."
        self.assertEqual(len(discount_lines), 2, msg=msg)
        self.assertTrue(discount_lines[0].tax_ids != discount_lines[1].tax_ids, msg=msg)
        msg = ("Each discount lines should cover a single order line, the last one being under"
                 " the minimal amount to be discounted.")
        self.assertEqual(len(discount_lines.discounted_line_ids), 2, msg=msg)
        for dl in discount_lines:
            discounted_line = dl.discounted_line_ids
            self.assertEqual(len(discounted_line), 1, msg=msg)
            self.assertTrue(discounted_line in (order.order_line[0], order.order_line[2]), msg=msg)
            self.assertEqual(dl.tax_ids, dl.discounted_line_ids.tax_ids, msg=msg)

    def test_reward_fixed_price_applies_only_once_for_same_product(self):
        # TODO EDM
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "3 for 15",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed', 'fixed_amount_per_unit': 5, 'required_points': 3
            })],
        })

    def test_multiple_rewards_fixed_price_applies_on_different_products(self):
        # TODO EDM
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "3 for 15",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed', 'fixed_amount_per_unit': 5, 'required_points': 3
            })],
        })

    def test_reward_fixed_price_do_not_discount_fixed_tax(self):
        # TODO EDM
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "3 for 15",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed', 'fixed_amount_per_unit': 5, 'required_points': 3
            })],
        })

    # === MIXED REWARDS TESTS === #

    def test_reward_specific_product_with_prorata_when_cheapest_already_applied(self):
        """ Check the application of a specific reward is computed based on what isn't yet
        discounted. """

        self.env['loyalty.program'].search([]).action_archive()

        # Using the same setup as test_reward_cheapest_product_applied_multiple_times
        cheapest_promo = self.env['loyalty.program'].create({
            'name': "Second cheapest at 50%",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'discount': 50, 'discount_applicability': 'cheapest', 'clear_wallet': False,
            })],
        })

        specific_promo = self.env['loyalty.program'].create({
            'name': "Reduction of 10%",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'discount': 10,
                'discount_applicability': 'specific',
                'discount_product_ids': self.product_C,
                'clear_wallet': False,
            })],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_A.id,
                    'product_uom_qty': 1,
                    'price_unit': 100,  # price_total tax included: 115 (15% tax)
                }),
                Command.create({
                    'product_id': self.product_B.id,
                    'product_uom_qty': 1,
                    'price_unit': 15,  # price_total tax included: 17.25 (15% tax)
                }),
                Command.create({
                    'product_id': self.product_C.id,
                    'product_uom_qty': 3,
                    'price_unit': 333,  # price_total tax included: 333 (No tax)
                }),
            ]
        })

        order._update_programs_and_rewards()
        self._claim_reward(order, program=cheapest_promo)

        msg = (
            f"Total amount should be 907.25 (previous total - 100*1.15*0.5 - 333*0.5 discounted)"
            f" and not {order.amount_total}."
        )
        self.assertEqual(float_compare(order.amount_total, 907.25, precision_rounding=3), 0, msg)

        self._claim_reward(order, program=specific_promo)

        msg = (
            f"Total amount should be 824 (previous total - 2*333*0.1 - 0.5*333*0.1)"
            f" and not {order.amount_total}. One of the 3 products already has a 50% discount."
        )
        self.assertEqual(float_compare(order.amount_total, 824, precision_rounding=3), 0, msg)

    def test_rewards_fixed_price_compatible_with_discount_on_order(self):
        # TODO EDM
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "3 for 15",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed', 'fixed_amount_per_unit': 5, 'required_points': 3
            })],
        })

    def test_rewards_fixed_price_incompatible_with_discount_on_same_line(self):
        # TODO EDM
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "3 for 15",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed', 'fixed_amount_per_unit': 5, 'required_points': 3
            })],
        })

    def test_any_line_discount_incompatible_with_fixed_price_discount_on_same_line(self):
        # TODO EDM even in the code ==> assert raise
        self.env['loyalty.program'].search([]).action_archive()

        promotion_program = self.env['loyalty.program'].create({
            'name': "3 for 15",
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [Command.create({'reward_point_amount': '1', 'reward_point_mode': 'unit'})],
            'reward_ids': [Command.create({
                'reward_type': 'fixed', 'fixed_amount_per_unit': 5, 'required_points': 3
            })],
        })
