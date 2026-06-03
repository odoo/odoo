from odoo import api, models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    @api.model
    def default_get(self, fields_list):
        active_moves = (
            self.env['account.move'].browse(self.env.context.get('active_ids', []))
            if self.env.context.get('active_model') == 'account.move'
            else self.env['account.move']
        )

        if active_moves:
            cn_moves = active_moves.filtered(lambda move: move.country_code == 'CN')
            cn_moves._check_l10n_cn_output_vat_offset_direct_modification()

        return super().default_get(fields_list)
