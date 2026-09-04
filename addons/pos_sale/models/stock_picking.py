# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        """ Override to unlink pickings that end up having no moves.
        This happens when all lines are filtered out by _create_move_from_pos_order_lines.
        We do this to avoid "ghost" pickings (in draft state) that block delivery calculations.
        """
        pickings = super()._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type, partner)
        for picking in pickings:
            if not picking.move_ids:
                picking.unlink()
        return pickings.exists()

    def _create_move_from_pos_order_lines(self, lines):
        lines_to_unreserve = self.env['pos.order.line']
        for line in lines:
            if line.order_id.shipping_date:
                continue
            if any(wh != line.order_id.config_id.warehouse_id for wh in line.sale_order_line_id.move_ids.location_id.warehouse_id):
                continue
            lines_to_unreserve |= line
        lines_to_unreserve.sale_order_line_id.move_ids.filtered(lambda ml: ml.state not in ['cancel', 'done'])._do_unreserve()
        lines_for_moves = lines.filtered(
            lambda l: not l.sale_order_line_id
            or (not (l.sale_order_line_id and 'is_rental' in l.sale_order_line_id._fields and l.sale_order_line_id['is_rental'])
                and (l.sale_order_line_id.has_valued_move_ids() or not l.sale_order_line_id.move_ids))
            or (l.sale_order_line_id == l.refunded_orderline_id.sale_order_line_id)
            or (l.sale_order_line_id.move_ids and all(m.state == 'cancel' for m in l.sale_order_line_id.move_ids))
        )
        return super()._create_move_from_pos_order_lines(lines_for_moves)
