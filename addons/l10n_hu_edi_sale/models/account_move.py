# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_hu_get_special_invoice_type(self):
        self.ensure_one()

        if self.move_type == "out_invoice":
            # This gives True if every line is a downpayment => Advance Invoice
            if self._is_downpayment():
                return "advance"
            # if any line is downpayment, but not every, than this is a Final Invoice
            if not self._is_downpayment() and any(self.invoice_line_ids.mapped("is_downpayment")):
                return "final"

        return super()._l10n_hu_get_special_invoice_type()
