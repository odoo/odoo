# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def _compute_document_type(self):
        """ If a l10n_latam_document_type_id was set, change it in the case of Brazil to be
        the same as the move that is being reversed.
        """
        res = super()._compute_document_type()
        for reversal in self.filtered("l10n_latam_document_type_id"):
            # LATAM invoices are guaranteed to be just one by _compute_documents_info().
            move = reversal.move_ids[0]
            if move.country_code == "BR":
                reversal.l10n_latam_document_type_id = move.l10n_latam_document_type_id

        return res
