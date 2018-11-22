# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _get_document_iterate_key(self, move_raw_id):
        return super(MrpProduction, self)._get_document_iterate_key(move_raw_id) or 'created_purchase_line_id'

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.multi
    def _compute_qty_received(self):
        super(PurchaseOrderLine, self)._compute_qty_received()
        for line in self:
            if line.qty_received_method == 'stock_moves' and line.move_ids and line.product_id.id not in line.move_ids.mapped('product_id').ids:
                bom = self.env['mrp.bom']._bom_find(product=line.product_id, company_id=line.company_id.id)
                if bom and bom.type == 'phantom':
                    line.qty_received = line._get_bom_delivered(bom=bom)

    def _get_bom_delivered(self, bom=False):
        self.ensure_one()

        # In the case of a kit, we need to check if all components are shipped. Since the BOM might
        # have changed, we don't compute the quantities but verify the move state.
        if bom:
            moves = self.move_ids.filtered(lambda m: m.picking_id and m.picking_id.state != 'cancel')
            bom_delivered = all([move.state == 'done' for move in moves])
            if bom_delivered:
                return self.product_qty
            else:
                return 0.0

    def _get_upstream_documents_and_responsibles(self, visited):
        return [(self.order_id, self.order_id.user_id, visited)]

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super(StockMove, self)._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if self.purchase_line_id:
            vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

