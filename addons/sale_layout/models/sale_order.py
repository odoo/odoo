# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.addons.sale_layout.models.sale_layout import grouplines


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def sale_layout_lines(self):
        """
        Returns order lines from a specified sale ordered by
        sale_layout_category sequence. Used in sale_layout module.
        """
        self.ensure_one()
        return grouplines(self.order_line, lambda x: x.sale_layout_cat_id)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _order = 'order_id, categ_sequence, sale_layout_cat_id, sequence, id'

    sale_layout_cat_id = fields.Many2one('sale_layout.category', string='Section')
    categ_sequence = fields.Integer(related='sale_layout_cat_id.sequence', string='Layout Sequence', store=True)
        #  Store is intentionally set in order to keep the "historic" order.

    @api.multi
    def _prepare_invoice_line(self, qty):
        """Save the layout when converting to an invoice line."""
        self.ensure_one()
        invoice_vals = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        invoice_vals.update(sale_layout_cat_id=self.sale_layout_cat_id.id, categ_sequence=self.categ_sequence)
        return invoice_vals
