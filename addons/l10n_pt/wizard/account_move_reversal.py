from odoo import models
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        self.ensure_one()
        for move in self.move_ids:
            if move.journal_id.country_code == 'PT' and not self.reason:
                raise UserError(_("For Credit notes issued in Portugal, you need to specify a Reason"))
        return super().reverse_moves(is_modify=is_modify)
