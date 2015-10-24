# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.addons.sale_layout.models.sale_layout import grouplines


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def sale_layout_lines(self):
        """
        Returns invoice lines from a specified invoice ordered by
        sale_layout_category sequence. Used in sale_layout module.
        """
        self.ensure_one()
        return grouplines(self.invoice_line_ids, lambda x: x.sale_layout_cat_id)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    _order = 'invoice_id, categ_sequence, sequence, id'

    sale_layout_cat_id = fields.Many2one('sale_layout.category', string='Section')
    categ_sequence = fields.Integer(related='sale_layout_cat_id.sequence', string='Layout Sequence', store=True)
