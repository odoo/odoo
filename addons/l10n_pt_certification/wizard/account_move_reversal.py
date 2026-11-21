from odoo import models
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _prepare_default_reversal(self, move):
        values = super()._prepare_default_reversal(move)
        if move.journal_id.country_code == 'PT':
            values['l10n_pt_reversal_reason'] = self.reason
        return values

    def reverse_moves(self, is_modify=False):
        self.ensure_one()
        for move in self.move_ids:
            if move.journal_id.country_code == 'PT' and not self.reason:
                raise UserError(self.env._("For Credit Notes issued in Portugal, you need to specify a Reason."))
        # A credit note references the document number of the invoice it rectifies.
        self.move_ids._l10n_pt_check_issued(self.env._("A credit note"))
        return super().reverse_moves(is_modify=is_modify)
