from odoo import models


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        # EXTENDS 'account_debit_note'
        default_values = super()._prepare_default_values(move)
        if self.country_code == 'PK' and self.reason:
            default_values.update({'l10n_pk_edi_refund_reason': self.reason})
        return default_values
