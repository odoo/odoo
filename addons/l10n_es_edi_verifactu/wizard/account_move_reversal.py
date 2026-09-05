from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _modify_default_reverse_values(self, origin_move):
        # EXTEND 'account'
        values = super()._modify_default_reverse_values(origin_move)
        values['l10n_es_edi_verifactu_substituted_entry_id'] = origin_move.id
        # A substitution keeps move_type 'out_invoice', but for VeriFactu it's still a correction
        # (TipoRectificativa='S'), so it needs an R4/R5 invoice type like any other correction.
        values['l10n_es_invoice_type'] = 'R5' if origin_move.l10n_es_invoice_type in ('F2', 'R5') else 'R4'
        return values
