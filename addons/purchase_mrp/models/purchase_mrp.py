# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_received = fields.Float(compute='_compute_qty_received', string="Received Qty", store=True)

    def _compute_qty_received(self):
        super(PurchaseOrderLine, self)._compute_qty_received()
        for line in self.filtered(lambda x: x.move_ids and x.product_id.id not in x.move_ids.mapped('product_id').ids):
            bom = self.env['mrp.bom']._bom_find(product=line.product_id, company_id=line.company_id.id)
            if bom and bom.type == 'phantom':
                line.qty_received = line._get_bom_delivered(bom=bom)

    def _get_bom_delivered(self, bom=False):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # In the case of a kit, we need to check if all components are received or not.
        # nothing policy. A product can have several BoMs, we don't know which one was used when the
        # receipt was created.
        bom_delivered = {}
        if bom:
            bom_delivered[bom.id] = False
            product_uom_qty_bom = self.product_uom._compute_quantity(self.product_qty, bom.product_uom_id) / bom.product_qty
            boms, lines = bom.explode(self.product_id, product_uom_qty_bom)
            for bom_line, data in lines:
                qty = 0.0
                for move in self.move_ids.filtered(lambda x: x.state == 'done' and x.product_id == bom_line.product_id):
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, bom_line.product_uom_id)
                if float_compare(qty, data['qty'], precision_digits=precision) < 0:
                    bom_delivered[bom.id] = False
                    break
                else:
                    bom_delivered[bom.id] = True
        if bom_delivered and any(bom_delivered.values()):
            return self.product_qty
        elif bom_delivered:
            return 0.0
