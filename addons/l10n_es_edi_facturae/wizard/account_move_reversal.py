from odoo import models, fields


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_es_edi_facturae_reason_code = fields.Selection(
        selection=lambda self: self.env['account.move']._fields['l10n_es_edi_facturae_reason_code']._description_selection(self.env),
        string='Spanish Facturae EDI Reason Code',
        default='10'
    )

    def reverse_moves(self, is_modify=False):
        # Extends account_account
        res = super(AccountMoveReversal, self).reverse_moves(is_modify)
        self.new_move_ids.l10n_es_edi_facturae_reason_code = self.l10n_es_edi_facturae_reason_code
        return res
