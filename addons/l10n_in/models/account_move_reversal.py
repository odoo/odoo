# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    def reverse_moves(self, is_modify=False):
        res = super().reverse_moves(is_modify)
        if self.company_id.country_id.code == "IN":
            for move_line, new_move_line in zip(self.move_ids.invoice_line_ids, self.new_move_ids.invoice_line_ids):
                if move_line.l10n_in_hsn_code != new_move_line.l10n_in_hsn_code:
                    new_move_line.l10n_in_hsn_code = move_line.l10n_in_hsn_code
        return res
