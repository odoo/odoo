# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons.l10n_pe_edi.models.account_move import REFUND_REASON


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_pe_edi_refund_reason = fields.Selection(
        selection=REFUND_REASON,
        string="Credit Reason",
        help="It contains all possible values for the refund reason according to Catalog No. 09")

    def _prepare_default_reversal(self, move):
        # OVERRIDE
        values = super()._prepare_default_reversal(move)
        if move.company_id.country_id.code == "PE" and move.journal_id.l10n_latam_use_documents:
            values.update({
                'l10n_pe_edi_refund_reason': self.l10n_pe_edi_refund_reason or '01',
                'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id or self.env.ref('l10n_pe.document_type07').id,
            })
        return values
