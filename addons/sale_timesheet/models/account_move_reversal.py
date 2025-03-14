from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        result = super().reverse_moves()
        if self.refund_method == 'cancel':
            moves = self.move_ids
            for move in moves:
                if move.move_type == 'out_invoice':
                    timesheet_lines = self.env['account.analytic.line'].search([
                        ('timesheet_invoice_id', '=', move.id)
                    ])
                    if timesheet_lines:
                        timesheet_lines.write({'timesheet_invoice_id': False})
        return result
