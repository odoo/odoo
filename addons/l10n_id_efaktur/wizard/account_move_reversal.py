# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def _modify_default_reverse_values(self, origin_move):
        # EXTEND 'account'
        values = super()._modify_default_reverse_values(origin_move)

        # The replacement eFaktur is to "correct" a detail from the original. If an e-Faktur
        # invoice has been sent to the government and the user needs to adjust it, they must send
        # an adjustment invoice, which refers to the original invoice in its tax number.
        if origin_move.l10n_id_efaktur_document:
            values.update({
                'l10n_id_replace_invoice_id': origin_move.id
            })
        return values
