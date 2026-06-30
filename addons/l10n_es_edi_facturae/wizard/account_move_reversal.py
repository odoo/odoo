from odoo import models, fields, _


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
        new_es_moves = self.new_move_ids.filtered(lambda move: move.country_code == 'ES')
        new_es_moves.l10n_es_edi_facturae_reason_code = self.l10n_es_edi_facturae_reason_code
        return res

    def _get_ref_string(self, move):
        if move._l10n_es_edi_facturae_get_default_enable():
            field = self.env['account.move']._fields['l10n_es_edi_facturae_reason_code']
            reason_descr = dict(field._description_selection(self.env)).get(self.l10n_es_edi_facturae_reason_code or '10')
            return _('Reversal of: %(move_name)s - %(reason)s', move_name=move.name, reason=reason_descr)
        return super()._get_ref_string(move)
