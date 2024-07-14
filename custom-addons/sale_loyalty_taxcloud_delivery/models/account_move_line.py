# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _is_delivery(self):
        """Part of the common interface between order lines and invoice lines.
           If we don't come from a sale.order, it will always be False.
           But we only really need that for coupon applications, and coupon can
           be present only if coming from a sale.order, so we're fine.
        """
        self.ensure_one()
        return any(self.mapped('sale_line_ids.is_delivery'))
