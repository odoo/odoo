# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _compute_cart_info(self):
        super(SaleOrder, self)._compute_cart_info()
        for order in self:
            reward_lines = order.website_order_line.filtered(lambda line: line.is_reward_line)
            order.cart_quantity -= int(sum(reward_lines.mapped('product_uom_qty')))
