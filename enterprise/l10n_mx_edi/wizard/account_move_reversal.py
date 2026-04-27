from odoo import models
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        self.ensure_one()
        for move in self.move_ids:
            if move.journal_id.country_code == 'MX' and move.tax_cash_basis_rec_id:
                raise UserError(_("You cannot reverse directly the cash basis entry, reverse the source move instead."))
        return super().reverse_moves(is_modify=is_modify)
