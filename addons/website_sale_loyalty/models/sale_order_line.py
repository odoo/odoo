# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_line_header(self):
        if self.is_reward_line:
            return self.name
        return super()._get_line_header()

    def _show_in_cart(self):
        # Hide discount lines from website_order_line, see `order._compute_website_order_line`
        return self.reward_id.reward_type != 'discount' and super()._show_in_cart()

    def _is_reorder_allowed(self):
        # Hide all types of rewards from reorder
        return not self.reward_id and super()._is_reorder_allowed()

    def unlink(self):
        if self.env.context.get('website_sale_loyalty_delete', False):
            disabled_rewards_per_order = defaultdict(lambda: self.env['loyalty.reward'])
            for line in self:
                if line.reward_id:
                    disabled_rewards_per_order[line.order_id] |= line.reward_id
            for order, rewards in disabled_rewards_per_order.items():
                order.disabled_auto_rewards += rewards
        return super().unlink()

    def _should_show_strikethrough_price(self):
        """ Override of `website_sale` to hide the strikethrough price for rewards. """
        return super()._should_show_strikethrough_price() and not self.is_reward_line

    def _is_sellable(self):
        """Override of `website_sale` to flag reward lines as not sellable.

        :return: Whether the line is sellable or not.
        :rtype: bool
        """
        return super()._is_sellable() and (
            not self.is_reward_line or self.reward_id.reward_type == 'product'
        )
