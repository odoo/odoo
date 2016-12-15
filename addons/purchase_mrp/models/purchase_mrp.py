# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'

    @api.multi
    def make_po(self):
        procurement_ids = super(ProcurementOrder, self).make_po()
        for procurement in self.browse(procurement_ids):
            if procurement.move_dest_id.raw_material_production_id:
                purchase = procurement.purchase_id
                purchase.message_post_with_view('mail.message_origin_link',
                         values={'self': purchase, 'origin': procurement.move_dest_id.raw_material_production_id},
                         subtype_id=self.env.ref('mail.mt_note').id)
        return procurement_ids

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
            product_uom_qty_bom = self.env['product.uom']._compute_qty_obj(self.product_uom, self.product_qty, bom.product_uom_id) / bom.product_qty
            boms, lines = bom.explode(self.product_id, product_uom_qty_bom)
            for bom_line, data in lines:
                qty = 0.0
                for move in self.move_ids.filtered(lambda x: x.state == 'done' and x.product_id == bom_line.product_id):
                    qty += self.env['product.uom']._compute_qty(move.product_uom.id, move.product_uom_qty, bom_line.product_uom_id.id)
                if float_compare(qty, data['qty'], precision_digits=precision) < 0:
                    bom_delivered[bom.id] = False
                    break
                else:
                    bom_delivered[bom.id] = True
        if bom_delivered and any(bom_delivered.values()):
            return self.product_qty
        elif bom_delivered:
            return 0.0
