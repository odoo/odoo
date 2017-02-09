# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _get_delivered_qty(self):
        """Computes the delivered quantity on sale order lines, based on done stock moves related to its procurements
        """
        self.ensure_one()
        qty = super(SaleOrderLine, self)._get_delivered_qty()
        for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped):
            if move.location_dest_id.usage == "internal" and move.to_refund_so:
                qty -= self.env['product.uom']._compute_qty_obj(move.product_uom, move.product_uom_qty, self.product_uom)
        return qty

class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund_so = fields.Boolean(string="To Refund in SO", default=False,
                                  help='Trigger a decrease of the delivered quantity in the associated Sale Order')

class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.multi
    def _create_returns(self):
        new_picking_id, pick_type_id = super(StockReturnPicking, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        for move in new_picking.move_lines:
            return_picking_line = self.product_return_moves.filtered(lambda r: r.move_id == move.origin_returned_move_id)
            if return_picking_line and return_picking_line.to_refund_so:
                move.to_refund_so = True

        return new_picking_id, pick_type_id


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    to_refund_so = fields.Boolean(string="To Refund in SO", help='Trigger a decrease of the delivered quantity in the associated Sale Order')
