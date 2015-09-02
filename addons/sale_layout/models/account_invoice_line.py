# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp
from openerp.osv import osv


class AccountInvoiceLine(osv.Model):
    _inherit = 'account.invoice.line'
    _order = 'invoice_id, categ_sequence, sequence, id'

    sale_layout_cat_id = openerp.fields.Many2one('sale_layout.category', string='Section')
    categ_sequence = openerp.fields.Integer(related='sale_layout_cat_id.sequence',
                                            string='Layout Sequence', store=True)
    _defaults = {
        'categ_sequence': 0
    }
