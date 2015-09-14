# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields
from openerp.addons.sale_layout.models.sale_layout import grouplines


class AccountInvoice(osv.Model):
    _inherit = 'account.invoice'

    def sale_layout_lines(self, cr, uid, ids, invoice_id=None, context=None):
        """
        Returns invoice lines from a specified invoice ordered by
        sale_layout_category sequence. Used in sale_layout module.

        :Parameters:
            -'invoice_id' (int): specify the concerned invoice.
        """
        ordered_lines = self.browse(cr, uid, invoice_id, context=context).invoice_line_ids
        # We chose to group first by category model and, if not present, by invoice name
        sortkey = lambda x: x.sale_layout_cat_id if x.sale_layout_cat_id else ''

        return grouplines(self, ordered_lines, sortkey)


import openerp

class AccountInvoiceLine(osv.Model):
    _inherit = 'account.invoice.line'
    _order = 'invoice_id, categ_sequence, sequence, id'

    sale_layout_cat_id = openerp.fields.Many2one('sale_layout.category', string='Section')
    categ_sequence = openerp.fields.Integer(related='sale_layout_cat_id.sequence',
                                            string='Layout Sequence', store=True)
    _defaults = {
        'categ_sequence': 0
    }
