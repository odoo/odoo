# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.tools.safe_eval import safe_eval


class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _inherit = ['loyalty.program']

    def get_available_rewards(self, order):
        """ Returns the list of rewards that the cart can get """
        client = order.partner_id
        rewards = []
        if client:
            spendable_points = tools.float_round(client.loyalty_points - order.spent_loyalty_points, 0, rounding_method='HALF-UP')
            for reward in self.reward_ids:
                if reward.minimum_points > spendable_points:
                    continue
                elif reward.reward_type == 'discount' and reward.point_cost > spendable_points:
                    continue
                elif reward.reward_type == 'gift' and reward.point_cost > spendable_points:
                    continue
                elif reward.reward_type == 'discount' and reward.discount_apply_on == 'specific_products':
                    if not (order.order_line.product_id & reward.discount_specific_product_ids):
                        continue
                elif reward.reward_type == 'discount' and reward.discount_type == 'fixed_amount' and order.amount_total < reward.minimum_amount:
                    continue
                elif reward in order.order_line.loyalty_reward_id:
                    continue
                rewards.append(reward)
        return rewards

    def contains_discount_reward(self, product_id):
        """Returns true if this reward contains the specified product_id as a discount reward"""
        return self.reward_ids.filtered(
            lambda reward: reward.reward_type == 'discount' and product_id in reward.discount_product_id.sudo().product_tmpl_id
        )


class LoyaltyRule(models.Model):
    _name = 'loyalty.rule'
    _inherit = ['loyalty.rule']

    valid_product_ids = fields.One2many('product.product', compute='_compute_valid_product_ids')

    @api.depends('rule_domain')
    def _compute_valid_product_ids(self):
        for rule in self:
            rule.valid_product_ids = self.env['product.product'].search(
                safe_eval(rule.rule_domain) if rule.rule_domain else []
            )

    def is_product_valid(self, product_id):
        """Avoid fetching the full product list if no domain is defined"""
        if self.rule_domain:
            return product_id in self.valid_product_ids
        return True


class LoyaltyReward(models.Model):
    _name = 'loyalty.reward'
    _inherit = ['loyalty.reward', 'image.mixin']

    def _get_discount_product_values(self):
        result = super()._get_discount_product_values()
        result['taxes_id'] = False
        result['supplier_taxes_id'] = False
        return result
