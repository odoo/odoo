# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    _order = 'invoice_id, categ_sequence, sequence, id'

    sale_layout_cat_id = fields.Many2one('sale_layout.category', string='Section')
    categ_sequence = fields.Integer(related='sale_layout_cat_id.sequence', string='Layout Sequence', store=True)
