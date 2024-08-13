# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSaleCouponProgramRules(TestSaleCouponCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.iPadMini = cls.env['product.product'].create({'name': 'Large Cabinet', 'list_price': 320.0})
        tax_15pc_excl = cls.env['account.tax'].create({
            'name': "15% Tax excl",
            'amount_type': 'percent',
            'amount': 15,
        })
        cls.product_delivery_poste = cls.env['product.product'].create({
            'name': 'The Poste',
            'type': 'service',
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
            'sale_ok': False,
            'purchase_ok': False,
            'list_price': 20.0,
            'taxes_id': [(6, 0, [tax_15pc_excl.id])],
        })
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'The Poste',
            'fixed_price': 20.0,
            'delivery_type': 'base_on_rule',
            'product_id': cls.product_delivery_poste.id,
        })
        cls.env['delivery.price.rule'].create([{
            'carrier_id': cls.carrier.id,
            'max_value': 5,
            'list_base_price': 20,
        }, {
            'carrier_id': cls.carrier.id,
            'operator': '>=',
            'max_value': 5,
            'list_base_price': 50,
        }, {
            'carrier_id': cls.carrier.id,
            'operator': '>=',
            'max_value': 300,
            'variable': 'price',
            'list_base_price': 0,
        }])


    # Test a free shipping reward + some expected behavior
    # (automatic line addition or removal)

    def test_free_shipping_reward(self):
        # Test case 1: The minimum amount is not reached, the reward should
        # not be created
        self.immediate_promotion_program.active = False
        program = self.env['loyalty.program'].create({
            'name': 'Free Shipping if at least 100 euros',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_amount': 100,
                'minimum_amount_tax_mode': 'incl',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'shipping',
            })],
        })

        order = self.env['sale.order'].create({
            'partner_id': self.steve.id,
        })

        # Price of order will be 5*1.15 = 5.75 (tax included)
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_B.id,
                'name': 'Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self._auto_rewards(order, program)
        self.assertEqual(len(order.order_line.ids), 1)

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id,
            'default_carrier_id': self.env['delivery.carrier'].search([])[1]
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        self._auto_rewards(order, program)
        self.assertEqual(len(order.order_line.ids), 2)

        # Test Case 1b: amount is not reached but is on a threshold
        # The amount of deliverable product + the one of the delivery exceeds the minimum amount
        # yet the program shouldn't be applied
        # Order price will be 5.75 + 81.74*1.15 = 99.75
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_B.id,
                'name': 'Product 1B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
                'price_unit': 81.74,
            })
        ]})
        self._auto_rewards(order, program)
        self.assertEqual(len(order.order_line.ids), 3)

        # Test case 2: the amount is sufficient, the shipping should
        # be reimbursed
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': 'Product 1',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
                'price_unit': 0.30,
            })
        ]})

        self._auto_rewards(order, program)
        self.assertEqual(len(order.order_line.ids), 5)

        # Test case 3: the amount is not sufficient now, the reward should be removed
        order.write({'order_line': [
            (2, order.order_line.filtered(lambda line: line.product_id.id == self.product_A.id).id, False)
        ]})
        self._auto_rewards(order, program)
        self.assertEqual(len(order.order_line.ids), 3)

    def test_shipping_cost(self):
        # Free delivery should not be taken into account when checking for minimum required threshold
        p_minimum_threshold_free_delivery = self.env['loyalty.program'].create({
            'name': 'free shipping if > 872 tax excl',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_amount': 872,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'shipping',
            })]
        })
        p_2 = self.env['loyalty.program'].create({
            'name': '10% reduction if > 872 tax excl',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_amount': 872,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })]
        })
        programs = (p_minimum_threshold_free_delivery | p_2)
        order = self.empty_order
        self.iPadMini.taxes_id = self.tax_10pc_incl
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'Large Cabinet',
            'product_uom_qty': 3.0,
            'order_id': order.id,
        })
        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 3, "We should get the 10% discount line since we bought 872.73$ and a free shipping line with a value of 0")
        self.assertEqual(order.order_line.filtered(lambda l: l.reward_id.reward_type == 'shipping').price_unit, 0)
        self.assertEqual(order.amount_total, 960 * 0.9)
        order.carrier_id = self.env['delivery.carrier'].search([])[1]

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id,
            'default_carrier_id': self.env['delivery.carrier'].search([])[1]
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 4, "We should get both rewards regardless of applying order.")

        p_minimum_threshold_free_delivery.sequence = 10
        (order.order_line - sol1).unlink()
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id,
            'default_carrier_id': self.env['delivery.carrier'].search([])[1]
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()
        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 4, "We should get both rewards regardless of applying order.")

    def test_shipping_cost_numbers(self):
        # Free delivery should not be taken into account when checking for minimum required threshold
        p_1 = self.env['loyalty.program'].create({
            'name': 'Free shipping if > 872 tax excl',
            'trigger': 'with_code',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'free_shipping',
                'minimum_amount': 872,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'shipping',
            })],
        })
        p_2 = self.env['loyalty.program'].create({
            'name': 'Buy 4 large cabinet, get one for free',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'product_ids': self.iPadMini,
                'minimum_qty': 4,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.iPadMini.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })
        programs = (p_1 | p_2)
        order = self.empty_order
        self.iPadMini.taxes_id = self.tax_10pc_incl
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'Large Cabinet',
            'product_uom_qty': 3.0,
            'order_id': order.id,
        })

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id,
            'default_carrier_id': self.carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()
        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(order.reward_amount, 0)
        # Shipping is 20 + 15%tax
        self.assertEqual(sum([line.price_total for line in order._get_no_effect_on_threshold_lines()]), 23)
        self.assertEqual(order.amount_untaxed, 872.73 + 20)

        self._apply_promo_code(order, 'free_shipping')
        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 3, "We should get the delivery line and the free delivery since we are below 872.73$")
        self.assertEqual(order.reward_amount, -20)
        self.assertEqual(sum([line.price_total for line in order._get_no_effect_on_threshold_lines()]), 0)
        self.assertEqual(order.amount_untaxed, 872.73)

        sol1.product_uom_qty = 4
        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 4, "We should get a free Large Cabinet")
        self.assertEqual(order.reward_amount, -20 - 320)
        self.assertEqual(sum([line.price_total for line in order._get_no_effect_on_threshold_lines()]), 0)
        self.assertEqual(order.amount_untaxed, 1163.64)

        programs |= self.env['loyalty.program'].create({
            'name': '20% reduction on large cabinet in cart',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 20,
                'discount_mode': 'percent',
                'discount_applicability': 'cheapest',
            })]
        })
        self._auto_rewards(order, programs)
        # 872.73 - (20% of 1 iPad) = 872.73 - 58.18 = 814.55
        self.assertAlmostEqual(order.amount_untaxed, 1105.46, 2, "One large cabinet should be discounted by 20%")

    def test_free_shipping_reward_last_line(self):
        """
            The free shipping reward cannot be removed if it is the last item in the sale order.
            However, we calculate its sequence so that it is the last item in the sale order.
            This can create an error if a default sequence is not determined.
        """
        self.immediate_promotion_program.active = False
        # Create a loyalty program
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'GIFT Free Shipping',
            'program_type': 'loyalty',
            'applies_on': 'both',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                    'reward_point_mode': 'money',
                    'reward_point_amount': 1,
                })],
            'reward_ids': [(0, 0, {
                'reward_type': 'shipping',
                'required_points': 100,
            })],
        })
        # Add points to a partner to trigger the promotion
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.steve.id,
            'points': 250,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.steve.id,
        })
        # Check if we can claim the free shipping reward
        order._update_programs_and_rewards()
        claimable_rewards = order._get_claimable_rewards()
        self.assertEqual(len(claimable_rewards), 1)
        # Try to apply the loyalty card to the sale order
        self._apply_promo_code(order, loyalty_card.code)
        # Check if there is an error in the sequence
        # via `_apply_program_reward` in `apply_promo_code` method

    def test_nothing_delivered_nothing_to_invoice(self):
        program = self.env['loyalty.program'].create({
            'name': '10% reduction on all orders',
            'trigger': 'auto',
            'program_type': 'promotion',
            'rule_ids': [Command.create({
                'minimum_amount': 50,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })]
        })
        product = self.env['product.product'].create({
            'name': 'Test product',
            'type': 'consu',
            'list_price': 200.0,
            'invoice_policy': 'delivery',
        })
        order = self.empty_order
        self.env['sale.order.line'].create({
            'product_id': product.id,
            'order_id': order.id,
        })
        self._auto_rewards(order, program)
        self.assertNotEqual(order.reward_amount, 0)
        self.assertEqual(order.invoice_status, 'no')
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id,
            'default_carrier_id': self.carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()
        order.action_confirm()
        self.assertEqual(order.delivery_set, True)
        self.assertEqual(order.invoice_status, 'no')

    def test_delivery_shant_count_toward_quantity_bought(self):

        # Create promotion: 10% for everything
        discount_program = self.env['loyalty.program'].create({
            'name': '10 percent off order with min. 2 products',
            'trigger': 'auto',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'minimum_qty': 2,
                'minimum_amount':0,
            })],
           'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10.0,
                'discount_applicability': 'order',
            })],
        })

        # Create an order including: product and delivery
        order = self.empty_order
        self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': self.iPadMini.name,
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })
        self.env['sale.order.line'].create({
            'product_id': self.product_delivery_poste.id,
            'name': 'Free delivery charges\nFree Shipping',
            'product_uom_qty': 1.0,
            'order_id': order.id,
            'is_delivery': True,
        })

        # Calculate promotions
        self._auto_rewards(order, discount_program)

        # Make sure the promotion is NOT added
        err_msg = "No reward lines should be created as the delivery line shouldn't be included in the promotion calculation"
        self.assertEqual(len(order.order_line.ids), 2, err_msg)

    def test_free_shipping_should_be_removed_when_rules_are_not_met(self):
        p_1 = self.env['loyalty.program'].create({
            'name': 'Free shipping if > 872 tax excl',
            'trigger': 'with_code',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'free_shipping',
                'minimum_amount': 872,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'shipping',
            })],
        })
        programs = (p_1)
        order = self.empty_order
        self.iPadMini.taxes_id = self.tax_10pc_incl
        sol1 = self.env['sale.order.line'].create({
            'product_id': self.iPadMini.id,
            'name': 'Large Cabinet',
            'product_uom_qty': 3.0,
            'order_id': order.id,
        })

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': order.id,
            'default_carrier_id': self.carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()
        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(order.reward_amount, 0)
        # Shipping is 20 + 15%tax
        self.assertEqual(sum(line.price_total for line in order._get_no_effect_on_threshold_lines()), 23)
        self.assertEqual(order.amount_untaxed, 872.73 + 20)

        self._apply_promo_code(order, 'free_shipping')
        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 3, "We should get the delivery line and the free delivery since we are below 872.73$")
        self.assertEqual(order.reward_amount, -20)
        self.assertEqual(sum(line.price_total for line in order._get_no_effect_on_threshold_lines()), 0)
        self.assertEqual(order.amount_untaxed, 872.73)

        sol1.product_uom_qty = 1
        self._auto_rewards(order, programs)
        self.assertEqual(len(order.order_line.ids), 2, "We should loose the free delivery reward since we are above 872.73$")
        self.assertEqual(order.reward_amount, 0)

    def test_discount_reward_claimable_when_shipping_reward_already_claimed_from_same_coupon(self):
        """
        Check that a discount reward is still claimable after the shipping reward is claimed.
        """
        program = self.env['loyalty.program'].create({
            'name': '10% Discount & Shipping',
            'applies_on': 'current',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'rule_ids': [Command.create({'mode': 'with_code', 'code': '10PERCENT&SHIPPING'})],
            'reward_ids': [
                Command.create({
                    'reward_type': 'shipping',
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
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_B.id})]
        })

        ship_reward = program.reward_ids.filtered(lambda reward: reward.reward_type == 'shipping')
        discount_reward = program.reward_ids - ship_reward
        order._apply_program_reward(ship_reward, coupon)
        rewards = order._get_claimable_rewards()[coupon]
        msg = "The discount reward should still be applicable as only the shipping one was claimed."
        self.assertEqual(rewards, discount_reward, msg)
