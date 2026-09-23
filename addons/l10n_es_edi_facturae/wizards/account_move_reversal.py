from odoo import fields, models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    l10n_es_edi_facturae_reason_code = fields.Selection(
        selection=lambda self: (
            self.env["account.move"]
            ._fields["l10n_es_edi_facturae_reason_code"]
            ._description_selection(self.env)
        ),
        string="Spanish Facturae EDI Reason Code",
        default="10",
    )

    def reverse_moves(self, is_modify=False):
        # Extends account_account
        res = super().reverse_moves(is_modify)
        new_es_moves = self.new_move_ids.filtered(
            lambda move: move.country_code == "ES"
        )
        new_es_moves.l10n_es_edi_facturae_reason_code = (
            self.l10n_es_edi_facturae_reason_code
        )
        return res

    def _prepare_default_reversal(self, move):
        values = super()._prepare_default_reversal(move)
        if move._l10n_es_edi_facturae_get_default_enable():
            field = self.env["account.move"]._fields["l10n_es_edi_facturae_reason_code"]
            reason = dict(field._description_selection(self.env)).get(
                self.l10n_es_edi_facturae_reason_code or "10"
            )
            values["ref"] = self.env._(
                "Reversal of: %(move_name)s - %(reason)s",
                move_name=move.name,
                reason=reason,
            )
        return values
