# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    purchase_line_ids = fields.One2many('purchase.order.line', 'sale_line_id')

    @api.multi
    def _get_qty_procurement(self):
        self.ensure_one()
        qty = 0.0
        # People without purchase rights should be able to do this operation
        purchase_lines_sudo = self.sudo().purchase_line_ids
        if not self.move_ids.filtered(lambda r: r.state != 'cancel') and purchase_lines_sudo.filtered(lambda r: r.state != 'cancel'):
            purchase_lines = purchase_lines_sudo.filtered(lambda r: r.state != 'cancel')
            if purchase_lines:
                for po_line in purchase_lines:
                    qty += po_line.product_uom._compute_quantity(po_line.product_qty, self.product_uom, rounding_method='HALF-UP')
                return qty
            else:
                return super(SaleOrderLine, self)._get_qty_procurement()
        else:
            return super(SaleOrderLine, self)._get_qty_procurement()

    @api.model
    def create(self, vals):
        if 'product_uom_qty' in vals and vals.get('order_id'):
            order = self.env['sale.order'].browse(vals.get('order_id'))
            existing_line = order.order_line.filtered(
                lambda line: line.product_id.id == vals.get('product_id')
            )
            if existing_line:
                po_line = self.env['purchase.order.line'].search([
                    ('sale_line_id', 'in', existing_line.ids),
                    ('order_id.state', 'not in', ['cancel', 'done']),
                    ('product_id', '=', vals.get('product_id'))
                ])
                if po_line:
                    raise UserError(
                        _('Please reuse the order line with the same product for drop shipping instead of creating a new line which can not be linked!')
                    )
        res = super(SaleOrderLine, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if 'product_uom_qty' in vals:
            for line in self:
                po_line = self.env['purchase.order.line'].search([
                    ('sale_line_id', '=', line.id),
                    ('order_id.state', 'not in', ['cancel', 'done']),
                    ('product_id', '=', line.product_id.id)
                ])
                if po_line:
                    line.move_ids = po_line.move_ids

        res = super(SaleOrderLine, self).write(vals)
        return res

