# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CouponReward(models.Model):
    _name = 'coupon.reward'
    _inherit = ['reward.mixin']
    _description = "Coupon Reward"
    _rec_name = 'reward_description'

    # Product Reward
    reward_product_quantity = fields.Integer(string="Quantity", default=1, help="Reward product quantity")
    # Discount Reward
    reward_product_uom_id = fields.Many2one(related='reward_product_id.product_tmpl_id.uom_id', string='Unit of Measure', readonly=True)
    discount_line_product_id = fields.Many2one('product.product', string='Reward Line Product', copy=False,
        help="Product used in the sales order to apply the discount. Each coupon program has its own reward product for reporting purpose")

    def name_get(self):
        """
        Returns a complete description of the reward
        """
        result = []
        for reward in self:
            reward_string = ""
            if reward.reward_type == 'product':
                reward_string = _("Free Product - %s", reward.reward_product_id.name)
            elif reward.reward_type == 'discount':
                if reward.discount_type == 'percentage':
                    reward_percentage = str(reward.discount_percentage)
                    if reward.discount_apply_on == 'on_order':
                        reward_string = _("%s%% discount on total amount", reward_percentage)
                    elif reward.discount_apply_on == 'specific_products':
                        if len(reward.discount_specific_product_ids) > 1:
                            reward_string = _("%s%% discount on products", reward_percentage)
                        else:
                            reward_string = _(
                                "%(percentage)s%% discount on %(product_name)s",
                                percentage=reward_percentage,
                                product_name=reward.discount_specific_product_ids.name
                            )
                    elif reward.discount_apply_on == 'cheapest_product':
                        reward_string = _("%s%% discount on cheapest product", reward_percentage)
                elif reward.discount_type == 'fixed_amount':
                    program = self.env['coupon.program'].search([('reward_id', '=', reward.id)])
                    reward_string = _(
                        "%(amount)s %(currency)s discount on total amount",
                        amount=reward.discount_fixed_amount,
                        currency=program.currency_id.name
                    )
            result.append((reward.id, reward_string))
        return result
