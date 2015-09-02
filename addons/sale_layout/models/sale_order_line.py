# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _order = 'order_id, categ_sequence, sale_layout_cat_id, sequence, id'

    sale_layout_cat_id = fields.Many2one('sale_layout.category', string='Section')
    categ_sequence = fields.Integer(related='sale_layout_cat_id.sequence', string='Layout Sequence', store=True)
        #  Store is intentionally set in order to keep the "historic" order.

    @api.model
    def _prepare_order_line_invoice_line(self, line, account_id=False):
        """Save the layout when converting to an invoice line."""
        invoice_vals = super(SaleOrderLine, self)._prepare_order_line_invoice_line(line, account_id=account_id)
        invoice_vals.update(sale_layout_cat_id=line.sale_layout_cat_id.id, categ_sequence=line.categ_sequence)
        return invoice_vals
