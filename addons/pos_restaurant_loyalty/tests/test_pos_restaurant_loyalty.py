# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontend
from odoo.tests import tagged
from odoo import Command


@tagged("post_install", "-at_install")
class TestPoSRestaurantLoyalty(TestFrontend):
    def test_change_table_rewards_stay(self):
        """
        Test that make sure that rewards stay on the order when leaving the table
        """
        self.env['loyalty.program'].create({
            'name': 'My super program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("PosRestaurantRewardStay")
        order = self.env['pos.order'].search([])
        self.assertEqual(order.currency_id.round(order.amount_total), 1.98)

    def test_loyalty_reward_with_courses(self):
        """
        Ensure that a loyalty reward line remains in the cart
        when courses are applied in a restaurant POS order.
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['loyalty.program'].create({
            'name': '10% Discount on All Products',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'minimum_qty': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_loyalty_reward_with_courses')
        orders = self.pos_config.current_session_id.order_ids
        self.assertEqual(len(orders), 2)
        self.assertEqual(orders[0].currency_id.round(orders[0].amount_total), 1.98)
        self.assertEqual(len(orders[0].lines.filtered(lambda line: line.is_reward_line)), 1)
        self.assertEqual(orders[1].currency_id.round(orders[1].amount_total), 1.98)
        self.assertEqual(len(orders[1].lines.filtered(lambda line: line.is_reward_line)), 1)
