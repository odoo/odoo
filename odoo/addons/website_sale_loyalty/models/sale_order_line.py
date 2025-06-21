# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _show_in_cart(self):
        # Hide discount lines from website_order_line, see `order._compute_website_order_line`
        return self.reward_id.reward_type != 'discount' and super()._show_in_cart()

    def unlink(self):
        if self.env.context.get('website_sale_loyalty_delete', False):
            disabled_rewards_per_order = defaultdict(lambda: self.env['loyalty.reward'])
            for line in self:
                if line.reward_id:
                    disabled_rewards_per_order[line.order_id] |= line.reward_id
            for order, rewards in disabled_rewards_per_order.items():
                order.disabled_auto_rewards += rewards
        return super().unlink()
