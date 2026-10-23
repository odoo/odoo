from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        """While reversing an invoice, set the cancellation reason to the reversed move"""

        res = super()._prepare_default_reversal(move)
        if self.country_code == 'PK' and self.reason:
            res.update({'l10n_pk_edi_refund_reason': self.reason})
        return res
