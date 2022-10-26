# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged, new_test_user

@tagged('post_install', '-at_install')
class TestLoyalty(TransactionCase):

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
                    'reward_point_mode': 'money',
                    'reward_point_amount': 10,
                })],
                'reward_ids': [(0, 0, {})],
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
        _, ewallet_coupon = self.env['loyalty.card'].create([
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
