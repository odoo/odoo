# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class L10nPeEdiCancelWizard(models.TransientModel):
    _name = "l10n_pe_edi.cancel"
    _description = "Wizard to allow the cancellation of Peruvian documents"

    l10n_pe_edi_cancel_reason = fields.Char(
        string="Cancel Reason",
        required=True,
        help="Reason to cancel this invoice.")

    def button_cancel(self):
        self.ensure_one()
        moves = self.env['account.move'].browse(self._context.get('active_ids'))
        moves.l10n_pe_edi_cancel_reason = self.l10n_pe_edi_cancel_reason.strip()
        moves.button_cancel_posted_moves()
        return True
