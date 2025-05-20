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
        self.env['loyalty.program'].search([]).write({'active': False})
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
            'pos_config_ids': [Command.link(self.pos_config.id)],
        })
        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(
            "/pos/web?config_id=%d" % self.pos_config.id,
            "PosRestaurantRewardStay",
            login="pos_admin",
        )
        order = self.env['pos.order'].search([])
        self.assertEqual(order.currency_id.round(order.amount_total), 1.98)
