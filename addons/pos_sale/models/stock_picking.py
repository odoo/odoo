# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api,fields, models

from itertools import groupby


class StockPicking(models.Model):
    _inherit='stock.picking'


    @api.model
    def _get_stock_move_quantity_from_pos_order_line(self, order_lines):
        quantity = super(StockPicking, self)._get_stock_move_quantity_from_pos_order_line(order_lines)
        lines_with_so = order_lines.filtered(lambda l: l.sale_order_origin_id)
        lines_by_so = groupby(sorted(lines_with_so, key=lambda l: l.sale_order_origin_id.id), key=lambda l: l.sale_order_origin_id.id)
        for so, lines in lines_by_so:
            pos_lines = self.env['pos.order.line'].concat(*lines)
            qty_in_pos_line = sum(pos_lines.mapped('qty'))
            sale_order_origin = pos_lines[0].sale_order_origin_id
            if qty_in_pos_line > 0:
                qty_deleivered_in_so = sum(sale_order_origin.order_line.filtered(lambda l: l.product_id.id == pos_lines[0].product_id.id and l.qty_delivered > 0).mapped('qty_delivered'))
            else:
                qty_deleivered_in_so = sum(sale_order_origin.order_line.filtered(lambda l: l.product_id.id == pos_lines[0].product_id.id and l.qty_delivered < 0).mapped('qty_delivered'))
            quantity -= abs(qty_deleivered_in_so)
        return quantity
