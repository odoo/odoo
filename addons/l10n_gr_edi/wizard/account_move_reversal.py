from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        """When reversing an invoice, set the greece correlated move field on the new credit note"""
        res = super()._prepare_default_reversal(move)
        if self.country_code == 'GR' and move.l10n_gr_edi_mark:
            res['l10n_gr_edi_correlation_id'] = move.id
        return res
