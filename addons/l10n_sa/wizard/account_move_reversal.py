from odoo import fields, models
from odoo.addons.l10n_sa.models.zatca_mixin import ADJUSTMENT_REASONS


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_sa_reason = fields.Selection(string="ZATCA Reason", selection=ADJUSTMENT_REASONS)
    l10n_sa_invoice_type = fields.Selection(related='move_ids.l10n_sa_invoice_type')

    def _prepare_default_reversal(self, move):
        return {
            **super()._prepare_default_reversal(move),
            "l10n_sa_reason": self.l10n_sa_reason,
        }
