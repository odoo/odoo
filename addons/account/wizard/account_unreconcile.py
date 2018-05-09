from odoo import models, api


class AccountUnreconcile(models.TransientModel):
    _name = "account.unreconcile"
    _description = "Account Unreconcile"

    @api.multi
    def trans_unrec(self):
        lines = self.env['account.move.line'].get_active_records()
        if lines:
            lines.remove_move_reconcile()
        return {'type': 'ir.actions.act_window_close'}
