# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        super(PurchaseOrder, self)._onchange_requisition_id()
        if self.requisition_id:
            self.picking_type_id = self.requisition_id.picking_type_id.id


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po):
        res = super()._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po)
        supplierinfo = (values.get('supplier') or {}).get('supplierinfo')
        if supplierinfo and supplierinfo.purchase_requisition_line_id.requisition_id == po.requisition_id:
            res['requisition_line_id'] = supplierinfo.purchase_requisition_line_id.id
        return res

    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        supplierinfo = (values.get('supplier') or {}).get('supplierinfo', self.env['product.supplierinfo'])
        if req_line := supplierinfo.purchase_requisition_line_id:
            allowed_lines = (req_line, self.env['purchase.requisition.line'])
            lines = self.filtered(lambda pol: pol.requisition_line_id in allowed_lines).sorted(lambda l: l.requisition_line_id != req_line)
            return super(PurchaseOrderLine, lines)._find_candidate(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        return super()._find_candidate(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
