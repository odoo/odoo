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
