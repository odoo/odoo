# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    sale_line_id = fields.Many2one('sale.order.line')

    @api.multi
    def _prepare_stock_moves(self, picking):
        res = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        for re in res:
            re['sale_line_id'] = self.sale_line_id.id
        return res

    def _merge_in_existing_line(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        """ This function purpose is to be override with the purpose to forbide _run_buy  method
        to merge a new po line in an existing one.
        """
        if values.get('sale_line_id') and self.sale_line_id and self.sale_line_id.id != values.get('sale_line_id'):
            return False
        return super(PurchaseOrderLine, self)._merge_in_existing_line(product_id, product_qty, product_uom, location_id, name, origin, values)

    @api.multi
    def unlink(self):
        is_dropshipping = self.mapped('order_id').mapped('picking_type_id') == self.env.ref('stock_dropshipping.picking_type_dropship')
        for line in self:
            if line.sale_line_id and is_dropshipping:
                raise UserError(
                    _('Purchase Order Line %s (Qty: %s) in %s was created through the route dropshipping. '
                      'As deleting this line might create inconsistencies, please adapt changes for quantities through the correspondent line in Sale Order %s' % (line.name, line.product_qty, line.order_id.name, line.sale_line_id.order_id.name))
                )
        return super(PurchaseOrderLine, self).unlink()

    @api.multi
    def write(self, vals):
        if 'product_qty' in vals:
            is_dropshipping = self.mapped('order_id').mapped('picking_type_id') == self.env.ref('stock_dropshipping.picking_type_dropship')
            for line in self:
                if line.sale_line_id and is_dropshipping and vals.get('product_qty') != line.sale_line_id.product_uom_qty:
                    raise UserError(
                        _('Purchase Order Line %s (Qty: %s) in %s was created through the route dropshipping. '
                          'Please adapt changes for quantities through the correspondent line in Sale Order %s' % (line.name, line.product_qty, line.order_id.name, line.sale_line_id.order_id.name))
                    )

        res = super(PurchaseOrderLine, self).write(vals)
        return res


class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
        res = super(ProcurementRule, self)._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
        res['sale_line_id'] = values.get('sale_line_id', False)
        return res

    def _update_purchase_order_line(self, product_id, product_qty, product_uom, values, line, partner):
        if values.get('sale_line_id'):
            sale_line = self.env['sale.order.line'].browse(values.get('sale_line_id'))
            po_line = self.env['purchase.order.line'].search([
                ('sale_line_id', '=', values.get('sale_line_id')),
                ('order_id.state', 'not in', ['cancel', 'done']),
                ('product_id', '=', product_id.id)
            ])
            if po_line:
                product_qty = sale_line.product_qty - po_line.product_qty
        res = super(ProcurementRule, self)._update_purchase_order_line(product_id, product_qty, product_uom, values, line, partner)
        return res

    def _make_po_get_domain(self, values, partner):
        domain = super(ProcurementRule, self)._make_po_get_domain(values, partner)
        if values.get('sale_line_id'):
            domain_new = tuple()
            for term in domain:
                if term != ('state', '=', 'draft'):
                    domain_new += (tuple(term),)
                else:
                    domain_new += (('state', 'not in', ('cancel', 'done')),)
            domain = domain_new
        return domain
