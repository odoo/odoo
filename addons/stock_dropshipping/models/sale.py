# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    purchase_line_ids = fields.One2many('purchase.order.line', 'sale_line_id')

    @api.multi
    def _get_qty_procurement(self):
        # People without purchase rights should be able to do this operation
        qty = super(SaleOrderLine, self)._get_qty_procurement()
        for line in self:
            purchase_lines_sudo = line.sudo().purchase_line_ids.filtered(lambda r: r.state != 'cancel')
            if all(m.state == 'cancel' for m in line.move_ids) and purchase_lines_sudo:
                line_qty = 0.0
                for po_line in purchase_lines_sudo:
                    line_qty += po_line.product_uom._compute_quantity(po_line.product_qty, self.product_uom, rounding_method='HALF-UP')
                if line.id in qty:
                    qty[line.id] += line_qty
                else:
                    qty[line.id] = line_qty
        return qty
