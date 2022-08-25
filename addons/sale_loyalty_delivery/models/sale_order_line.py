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
