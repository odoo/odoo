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

    def _compute_qty_received(self):
        kit_lines = self.env['purchase.order.line']
        for line in self:
            if line.qty_received_method == 'stock_moves' and line.move_ids.filtered(lambda m: m.state != 'cancel' and m.bom_line_id):
                kit_bom = self.env['mrp.bom']._bom_find(product=line.product_id, company_id=line.company_id.id, bom_type='phantom')
                if kit_bom:
                    moves = line.move_ids.filtered(lambda m: m.state == 'done' and not m.scrapped)
                    order_qty = line.product_uom._compute_quantity(line.product_uom_qty, kit_bom.product_uom_id)
                    filters = {
                        'incoming_moves': lambda m: m.location_id.usage == 'supplier' and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                        'outgoing_moves': lambda m: m.location_id.usage != 'supplier' and m.to_refund
                    }
                    line.qty_received = moves._compute_kit_quantities(line.product_id, order_qty, kit_bom, filters)
                    kit_lines += line
        super(PurchaseOrderLine, self - kit_lines)._compute_qty_received()

    def _get_upstream_documents_and_responsibles(self, visited):
        return [(self.order_id, self.order_id.user_id, visited)]

    def _get_qty_procurement(self):
        self.ensure_one()
        # Specific case when we change the qty on a PO for a kit product.
        # We don't try to be too smart and keep a simple approach: we compare the quantity before
        # and after update, and return the difference. We don't take into account what was already
        # sent, or any other exceptional case.
        bom = self.env['mrp.bom'].sudo()._bom_find(product=self.product_id)
        if bom and bom.type == 'phantom' and 'previous_product_qty' in self.env.context:
            return self.env.context['previous_product_qty'].get(self.id, 0.0)
        return super()._get_qty_procurement()

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super(StockMove, self)._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        if self.purchase_line_id:
            vals['purchase_line_id'] = self.purchase_line_id.id
        return vals

