from odoo import fields, models

from odoo.addons.l10n_ae_ubl_pint.models.account_move import CREDIT_NOTE_REASONS


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_ae_credit_note_reason = fields.Selection(
        string='AE Credit Note Reason',
        selection=CREDIT_NOTE_REASONS,
    )

    def _prepare_default_reversal(self, move):
        return {
            **super()._prepare_default_reversal(move),
            'l10n_ae_credit_note_reason': self.l10n_ae_credit_note_reason,
        }
