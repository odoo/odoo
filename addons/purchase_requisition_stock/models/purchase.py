# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('requisition_ids')
    def _onchange_requisition_ids(self):
        super()._onchange_requisition_ids()
        if self.requisition_ids:
            self.picking_type_id = self.requisition_ids.picking_type_id.id


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po):
        requisition_line = self._get_procurement_requisition_line(values)
        if not requisition_line:
            # the price must come from the chosen pricelist, not from a blanket order of the same vendor
            product_id = product_id.with_context(exclude_blanket_orders=True)
        res = super()._prepare_purchase_order_line_from_procurement(
            product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po)
        res['requisition_line_id'] = requisition_line.id
        return res

    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        # only merge with a line following the same terms (the same agreement line, or none)
        requisition_line = self._get_procurement_requisition_line(values)
        lines = self.filtered(lambda line: line.requisition_line_id == requisition_line)
        return super(PurchaseOrderLine, lines)._find_candidate(
            product_id, product_qty, product_uom, location_id, name, origin, company_id, values)

    @api.model
    def _get_procurement_requisition_line(self, values):
        """ The agreement line of the pricelist chosen for a procurement, if any. """
        seller_info = values.get('supplier') or {}
        return seller_info.get('supplierinfo', self.env['product.supplierinfo']).purchase_requisition_line_id
