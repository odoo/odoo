from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _modify_default_reverse_values(self, origin_move):
        values = super()._modify_default_reverse_values(origin_move)
        values['l10n_es_edi_verifactu_substituted_entry_id'] = origin_move.id
        return values
