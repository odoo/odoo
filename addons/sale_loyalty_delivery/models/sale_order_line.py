# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def unlink(self):
        # Prevent unlinking of free shipping lines except if they are the last line remaining
        free_shipping_lines = self.filtered(lambda l: l.reward_id.reward_type == 'shipping')
        res = super(SaleOrderLine, self - free_shipping_lines).unlink()
        lines_per_order = defaultdict(lambda: self.env['sale.order.line'])
        for line in free_shipping_lines:
            lines_per_order[line.order_id] |= line
        lines_to_unlink = self.env['sale.order.line']
        for order in free_shipping_lines.order_id:
            if order.order_line and order.order_line == lines_per_order[order]:
                lines_to_unlink |= lines_per_order[order]
        if lines_to_unlink:
            super(SaleOrderLine, lines_to_unlink).unlink()
        return res

    def get_reward_line_price(self, product):
        return sum(self.order_id.order_line.filtered(
            lambda line: line.product_id == product).mapped('price_reduce_taxinc')
        ) / self.product_uom_qty if self.product_uom_qty else 0

    def get_global_discount(self):
        discount_amount = super().get_global_discount()
        reward_ids = self.order_id.get_reward_ids()
        for reward in reward_ids:
            if reward.reward_type == "discount":
                if reward.discount_applicability == "cheapest":
                    discount_amount += self.get_reward_line_price(reward.discount_line_product_id) if self == self.order_id._cheapest_line() else 0
                elif reward.discount_applicability in ("specific", "order"):
                    if reward.discount_applicability == "specific":
                        lines = self.order_id.order_line.filtered(
                            lambda line: line.product_id in reward.discount_product_ids and line.product_id == self.product_id
                        )
                    else:
                        lines = self.order_id.order_line.filtered(
                            lambda line: not (line.is_reward_line or line.is_delivery)
                        )
                    reward_line_amount = self.get_reward_line_price(reward.discount_line_product_id)
                    discount_amount += (self.price_reduce_taxinc / sum(lines.mapped('price_reduce_taxinc'))) * reward_line_amount if lines else 0
            elif reward.reward_type == "product" and self.product_id == reward.reward_product_id:
                discount_amount += self.get_reward_line_price(reward.discount_line_product_id)
        return discount_amount * -1
