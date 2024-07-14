# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("l10n_latam_document_type_id")
    def _compute_l10n_br_is_service_transaction(self):
        """Override."""
        for move in self:
            move.l10n_br_is_service_transaction = (
                move._l10n_br_is_avatax() and move.l10n_latam_document_type_id == self.env.ref("l10n_br.dt_SE")
            )
