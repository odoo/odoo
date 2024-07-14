# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    l10n_pe_edi_charge_reason = fields.Selection(
        selection=[
            ('01', 'Default interest'),
            ('02', 'Increase in value'),
            ('03', 'Penalties / other concepts'),
            ('11', 'Adjustments of export operations'),
            ('12', 'Adjustments affecting the IVAP'),
        ],
        string="Debit Reason",
        default='01',
        help="It contains all possible values for the refund reason according to Catalog No. 10")

    def _prepare_default_values(self, move):
        # OVERRIDE
        values = super()._prepare_default_values(move)
        if self.country_code == 'PE' and move.journal_id.l10n_latam_use_documents:
            values.update({
                'l10n_pe_edi_charge_reason': self.l10n_pe_edi_charge_reason,
                'l10n_latam_document_type_id': self.env.ref('l10n_pe.document_type08').id
            })
        return values
