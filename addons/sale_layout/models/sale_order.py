# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models
from openerp.addons.sale_layout.models.sale_layout import grouplines


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def sale_layout_lines(self):
        """
        Returns order lines from a specified sale ordered by
        sale_layout_category sequence. Used in sale_layout module.
        """
        sortkey = lambda x: x.sale_layout_cat_id if x.sale_layout_cat_id else ''

        return grouplines(self.order_line, sortkey)
