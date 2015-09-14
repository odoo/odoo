# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields
from openerp.addons.sale_layout.models.sale_layout import grouplines


class SaleOrder(osv.Model):
    _inherit = 'sale.order'

    def sale_layout_lines(self, cr, uid, ids, order_id=None, context=None):
        """
        Returns order lines from a specified sale ordered by
        sale_layout_category sequence. Used in sale_layout module.

        :Parameters:
            -'order_id' (int): specify the concerned sale order.
        """
        ordered_lines = self.browse(cr, uid, order_id, context=context).order_line
        sortkey = lambda x: x.sale_layout_cat_id if x.sale_layout_cat_id else ''

        return grouplines(self, ordered_lines, sortkey)


class SaleOrderLine(osv.Model):
    _inherit = 'sale.order.line'
    _columns = {
        'sale_layout_cat_id': fields.many2one('sale_layout.category',
                                              string='Section'),
        'categ_sequence': fields.related('sale_layout_cat_id',
                                         'sequence', type='integer',
                                         string='Layout Sequence', store=True)
        #  Store is intentionally set in order to keep the "historic" order.
    }

    _defaults = {
        'categ_sequence': 0
    }

    _order = 'order_id, categ_sequence, sale_layout_cat_id, sequence, id'

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Save the layout when converting to an invoice line."""
        invoice_vals = super(SaleOrderLine, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
        if line.sale_layout_cat_id:
            invoice_vals['sale_layout_cat_id'] = line.sale_layout_cat_id.id
        if line.categ_sequence:
            invoice_vals['categ_sequence'] = line.categ_sequence
        return invoice_vals
