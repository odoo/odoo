# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('move_ids', 'move_ids.stock_valuation_layer_ids', 'order_id.picking_ids.state')
    def _compute_purchase_price(self):
        lines_with_moves = self.filtered("move_ids")
        for line in lines_with_moves:
            line.purchase_price = line.product_id._compute_average_price(0, line.product_uom_qty, line.move_ids)
        return super(SaleOrderLine, self-lines_with_moves)._compute_purchase_price()
