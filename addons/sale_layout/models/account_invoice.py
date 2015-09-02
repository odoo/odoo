# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models
from openerp.addons.sale_layout.models.sale_layout import grouplines


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def sale_layout_lines(self):
        """
        Returns invoice lines from a specified invoice ordered by
        sale_layout_category sequence. Used in sale_layout module.
        """
        # We chose to group first by category model and, if not present, by invoice name
        sortkey = lambda x: x.sale_layout_cat_id if x.sale_layout_cat_id else ''

        return grouplines(self.invoice_line_ids, sortkey)
