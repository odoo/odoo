from odoo import fields, models
from odoo.addons.l10n_sa.models.zatca_mixin import ADJUSTMENT_REASONS


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    l10n_sa_reason = fields.Selection(string="ZATCA Reason", selection=ADJUSTMENT_REASONS)

    def _prepare_default_values(self, move):
        return {
            **super()._prepare_default_values(move),
            "l10n_sa_reason": self.l10n_sa_reason,
        }
