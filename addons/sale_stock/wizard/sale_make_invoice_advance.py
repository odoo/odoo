# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoice(self, order, so_line, amount):
        """ Overridden to activate the use of interim accounts for sale invoices
        in case the company uses anglo saxon accounting.
        """
        return super(SaleAdvancePaymentInv, self.with_context(default_anglo_saxon_interim_stock_entries=order.company_id.anglo_saxon_accounting))._create_invoice(order, so_line, amount)