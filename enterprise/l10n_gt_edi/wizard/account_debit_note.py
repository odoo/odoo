from odoo import models


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        # EXTENDS 'account_debit_note'
        default_values = super()._prepare_default_values(move)
        if self.country_code == 'GT':
            default_values.update({
                'l10n_gt_edi_doc_type': 'NDEB',
            })
        return default_values
