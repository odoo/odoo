from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        # For SG B2G, the reversal invoice number must be provided in the EDI credit note as the
        # related invoice ID.
        if move.l10n_sg_partner_is_statutory_board:
            res.update({'ref': move.name})
        return res
