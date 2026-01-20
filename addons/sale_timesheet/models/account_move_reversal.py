from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        if is_modify:
            moves = self.move_ids.filtered(lambda m: m.move_type == 'out_invoice')
            timesheets_sudo = self.env['account.analytic.line'].sudo().search([
                ('reinvoice_move_id', 'in', moves.ids),
            ])
            if timesheets_sudo:
                timesheets_sudo.write({'reinvoice_move_id': False})
        return super().reverse_moves(is_modify)
