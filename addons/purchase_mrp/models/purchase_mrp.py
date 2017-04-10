# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_received = fields.Float(compute='_compute_qty_received', string="Received Qty", store=True)

    def _compute_qty_received(self):
        phantom_lines = self.env['purchase.order.line']
        for line in self.filtered(lambda x: x.move_ids and x.product_id.id not in x.move_ids.mapped('product_id').ids):
            bom = self.env['mrp.bom']._bom_find(product=line.product_id, company_id=line.company_id.id)
            if bom and bom.type == 'phantom':
                line.qty_received = line._get_bom_delivered(bom=bom)
                phantom_lines |= line
        super(PurchaseOrderLine, self.filtered(lambda x:x not in phantom_lines))._compute_qty_received()

    def _get_bom_delivered(self, bom=False):
        self.ensure_one()

        # In the case of a kit, we need to check if some of components are shipped. Since the BOM might
        # have changed, we don't compute the quantities but verify the move state.
        if bom:
            move_product_dict = dict(map(lambda x: (x.id, {'done': 0.0, 'qty': 0.0}), self.move_ids.mapped('product_id')))
            for move in self.move_ids:
                move_product_dict[move.product_id.id]['qty'] += move.product_uom_qty
                if move.state == 'done':
                    move_product_dict[move.product_id.id]['done'] += move.product_uom_qty
            min_transfer = min(move_product_dict[key]['done'] / move_product_dict[key]['qty'] for key in move_product_dict)
            return min_transfer * self.product_qty
