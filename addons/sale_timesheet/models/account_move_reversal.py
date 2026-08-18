from odoo import models


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self, is_modify=False):
        timesheets_sudo = self.env['account.analytic.line']
        if is_modify:
            moves = self.move_ids.filtered(lambda m: m.move_type == 'out_invoice')
            timesheets_sudo = self.env['account.analytic.line'].sudo().search([
                ('reinvoice_move_id', 'in', moves.ids),
            ])
        reverse = super().reverse_moves(is_modify)
        if is_modify and timesheets_sudo:
            move_per_so_line = {}
            new_invoices = self.new_move_ids.filtered(lambda m: m.move_type == 'out_invoice')
            for line in new_invoices.invoice_line_ids:
                for so_line in line.sale_line_ids:
                    move_per_so_line.setdefault(so_line.id, line.move_id)
            for move, timesheets in timesheets_sudo.grouped(
                lambda t: move_per_so_line.get(t.so_line.id)
            ).items():
                if move:
                    timesheets.reinvoice_move_id = move
        return reverse
