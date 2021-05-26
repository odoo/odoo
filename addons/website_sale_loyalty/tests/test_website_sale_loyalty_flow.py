# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserPortal

@tagged('post_install', '-at_install')
class TestWebsiteSaleLoyaltyCartReward(HttpCaseWithUserPortal):

    def test_01_rewards_in_cart(self):
        """The goal of this test is to verify the way rewards are added/removed from/to cart."""
        self.partner_portal.loyalty_points = 250
        self.start_tour("/shop?search=Office Lamp", 'shop_cart_reward', login="portal")
        self.assertEqual(240, self.partner_portal.loyalty_points, "Points should be spent when order is confirmed")
        order = self.env['sale.order'].search([('order_line.loyalty_reward_id', '!=', False)], order='create_date desc', limit=1)
        order.write({'state': 'done'})
        self.assertEqual(640, self.partner_portal.loyalty_points, "Points should be gained when order is payed")
