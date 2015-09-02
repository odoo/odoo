# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv
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
