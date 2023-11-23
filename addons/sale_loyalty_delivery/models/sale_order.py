# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # delivery overrides

    def _compute_amount_total_without_delivery(self):
        res = super()._compute_amount_total_without_delivery()
        return res - sum(
            self.order_line.filtered(
                lambda l: l.coupon_id and l.coupon_id.program_type in ['ewallet', 'gift_card']
            ).mapped('price_unit')
        )

    # sale_loyalty overrides

    def _get_no_effect_on_threshold_lines(self):
        res = super()._get_no_effect_on_threshold_lines()
        return res + self.order_line.filtered(
            lambda line: line.is_delivery or line.reward_id.reward_type == 'shipping')

    def _get_lines_impacting_invoice_status(self):
        return super()._get_lines_impacting_invoice_status().filtered(
            lambda line: not line.is_reward_line
        )

    def _get_reward_values_free_shipping(self, reward, coupon, **kwargs):
        delivery_line = self.order_line.filtered(lambda l: l.is_delivery)
        taxes = delivery_line.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes = self.fiscal_position_id.map_tax(taxes)
        max_discount = reward.discount_max_amount or float('inf')
        return [{
            'name': _('Free Shipping - %s', reward.description),
            'reward_id': reward.id,
            'coupon_id': coupon.id,
            'points_cost': reward.required_points if not reward.clear_wallet else self._get_real_points_for_coupon(coupon),
            'product_id': reward.discount_line_product_id.id,
            'price_unit': -min(max_discount, delivery_line.price_unit or 0),
            'product_uom_qty': 1,
            'product_uom': reward.discount_line_product_id.uom_id.id,
            'order_id': self.id,
            'is_reward_line': True,
            'sequence': max(self.order_line.filtered(lambda x: not x.is_reward_line).mapped('sequence'), default=0) + 1,
            'tax_id': [(Command.CLEAR, 0, 0)] + [(Command.LINK, tax.id, False) for tax in taxes],
        }]

    def _get_reward_line_values(self, reward, coupon, **kwargs):
        self.ensure_one()
        if reward.reward_type == 'shipping':
            self = self.with_context(lang=self._get_lang())
            reward = reward.with_context(lang=self._get_lang())
            return self._get_reward_values_free_shipping(reward, coupon, **kwargs)
        return super()._get_reward_line_values(reward, coupon, **kwargs)

    def _get_claimable_rewards(self, forced_coupons=None):
        res = super()._get_claimable_rewards(forced_coupons)
        if any(reward.reward_type == 'shipping' for reward in self.order_line.reward_id):
            # Allow only one reward of type shipping at the same time
            filtered_res = {}
            for coupon, rewards in res.items():
                filtered_rewards = rewards.filtered(lambda r: r.reward_type != 'shipping')
                if filtered_rewards:
                    filtered_res[coupon] = filtered_rewards
            res = filtered_res
        return res
