# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class CouponReward(models.Model):
    _inherit = 'coupon.reward'
    _description = "Coupon Reward"

    reward_type = fields.Selection(selection_add=[('free_shipping', 'Free Shipping')])

    def name_get(self):
        result = []
        reward_names = super(CouponReward, self).name_get()
        free_shipping_reward_ids = self.filtered(lambda reward: reward.reward_type == 'free_shipping').ids
        for res in reward_names:
            result.append((res[0], res[0] in free_shipping_reward_ids and _("Free Shipping") or res[1]))
        return result
