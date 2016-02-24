# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _compute_analytic_qty(self, domain=None):
        lines = {}
        if not domain:
            # To filter on analyic lines linked to an expense
            domain = [('so_line', 'in', self.ids), ('amount', '<=', 0.0)]
        data = self.env['account.analytic.line'].read_group(
            domain,
            ['so_line', 'unit_amount', 'product_uom_id'], ['product_uom_id', 'so_line'], lazy=False
        )
        for d in data:
            if not d['product_uom_id']:
                continue
            line = self.browse(d['so_line'][0])
            lines.setdefault(line, 0.0)
            uom = self.env['product.uom'].browse(d['product_uom_id'][0])
            if line.product_uom.category_id == uom.category_id:
                qty = self.env['product.uom']._compute_qty_obj(uom, d['unit_amount'], line.product_uom)
            else:
                qty = d['unit_amount']
            lines[line] += qty

        for line, qty in lines.items():
            line.qty_delivered = qty
        return True


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    so_line = fields.Many2one('sale.order.line', string='Sale Order Line')
