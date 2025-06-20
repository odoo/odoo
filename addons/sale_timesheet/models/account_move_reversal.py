from odoo import models

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        result = super(AccountMoveReversal, self).reverse_moves()
        moves = self.move_ids
        timesheet_lines = self.env['account.analytic.line'].search([
            ('timesheet_invoice_id', 'in', moves.ids)
        ])
        if timesheet_lines:
            timesheet_lines.write({'timesheet_invoice_id': False})
        return result
