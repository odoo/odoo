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

    def _get_not_rewarded_order_lines(self):
        """Exclude delivery lines from consideration for reward points."""
        order_line = super()._get_not_rewarded_order_lines()
        return order_line.filtered(lambda line: not line.is_delivery)

    def _get_reward_values_free_shipping(self, reward, coupon, **kwargs):
        delivery_line = self.order_line.filtered(lambda l: l.is_delivery)[:1]
        taxes = delivery_line.product_id.taxes_id._filter_taxes_by_company(self.company_id)
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
            'order_id': self.id,
            'is_reward_line': True,
            'sequence': max(self.order_line.filtered(lambda x: not x.is_reward_line).mapped('sequence'), default=0) + 1,
            'tax_ids': [Command.clear()] + [Command.link(tax.id) for tax in taxes],
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

    def _get_line_global_discount(self):
        """ Overrides the original method to apply rewards and loyalty discounts. """
        if not self:
            return {}

        sale_line_discount_dict = super()._get_line_global_discount()
        for so in self:
            invoicable_lines = so.order_line.filtered(lambda line: line._can_be_invoiced_alone())
            reward_lines = (so.order_line - invoicable_lines).filtered(lambda line: line.is_reward_line)
            if not invoicable_lines or sum(invoicable_lines.mapped("price_reduce_taxinc")) == 0:
                continue
            for line in reward_lines:
                lines = invoicable_lines
                reward = line.reward_id
                reward_line_amount = line.price_total
                if reward.reward_type == "discount":
                    if reward.discount_applicability == "cheapest" and (cheapest_line := so._cheapest_line()):
                        sale_line_discount_dict[cheapest_line.id] -= reward_line_amount / cheapest_line.product_uom_qty
                        continue
                    elif reward.discount_applicability == "specific":
                        lines = invoicable_lines.filtered(lambda line: line.product_id in reward.discount_product_ids)
                elif reward.reward_type == "product" and reward.reward_product_id in lines.mapped('product_id'):
                    reward_line_amount = -(reward.reward_product_id.lst_price * line.product_uom_qty)
                for line in lines:
                    total_lines_price = sum(lines.mapped("price_reduce_taxinc"))
                    line_price_share = (line.price_reduce_taxinc / total_lines_price) * reward_line_amount
                    sale_line_discount_dict[line.id] -= line_price_share / line.product_uom_qty
        return sale_line_discount_dict
