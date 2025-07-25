# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.tests import HttpCase, tagged

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponNumbersCommon


@tagged('post_install', '-at_install')
class TestSaleLoyaltyCouponReward(HttpCase, TestSaleCouponNumbersCommon):

    def test_program_coupon_reward_tour(self):

        self.immediate_promotion_program.active = False
        self.env['loyalty.program'].create({
            'name': "Get 10% discount on buying Product A",
            'program_type': "coupons",
            'applies_on': "current",
            'trigger': "with_code",
            'rule_ids': [Command.create({
                'product_ids': self.product_A,
                'minimum_qty': 1,
                'code': "test_10dis",
            })],
            'reward_ids': [Command.create({
                'reward_type': "discount",
                'discount_mode': "percent",
                'discount': 10,
                'discount_applicability': "order",
            })],
        })
        self.start_tour("/", "program_coupon_reward_tour", login="admin")
