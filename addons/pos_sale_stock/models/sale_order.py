# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['picking_ids']


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('pos_order_line_ids.order_id.picking_ids', 'pos_order_line_ids.order_id.picking_ids.state', 'pos_order_line_ids.refund_orderline_ids.order_id.picking_ids.state')
    def _compute_qty_delivered(self):
        super()._compute_qty_delivered()

    def _prepare_qty_delivered(self):
        delivered_qties = super()._prepare_qty_delivered()

        def _get_pos_delivered_qty(sale_line, pos_lines):
            if all(picking.state == "done" for picking in pos_lines.order_id.picking_ids):
                # Sum converted quantities from POS to sale order UoM
                return sum(self._convert_qty(sale_line, pos_line.qty, "p2s") for pos_line in pos_lines)
            return 0

        def line_filter(line):
            return line.order_id.state not in ["cancel", "draft"]

        for sale_line in self.filtered(lambda line: line.product_id.type != "service"):
            pos_line_ids = sale_line.sudo().pos_order_line_ids
            pos_qty = _get_pos_delivered_qty(sale_line, pos_line_ids.filtered(line_filter))
            if pos_qty != 0:
                delivered_qties[sale_line] += pos_qty

            refund_qty = _get_pos_delivered_qty(sale_line, pos_line_ids.refund_orderline_ids.filtered(line_filter))
            if refund_qty != 0:
                delivered_qties[sale_line] += refund_qty
        return delivered_qties

    def _get_read_converted_extra_items(self, sale_line):
        extra_items = super()._get_read_converted_extra_items(sale_line)
        if sale_line.product_id.tracking in ['lot', 'serial']:
            move_lines = sale_line.move_ids.move_line_ids.filtered(lambda ml: ml.product_id.id == sale_line.product_id.id)
            extra_items['lot_names'] = move_lines.lot_id.mapped('name')
            lot_qty_by_name = {}
            for line in move_lines:
                lot_qty_by_name[line.lot_id.name] = lot_qty_by_name.get(line.lot_id.name, 0.0) + line.quantity
            extra_items['lot_qty_by_name'] = lot_qty_by_name
        return extra_items
