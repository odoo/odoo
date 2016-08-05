from odoo import models, fields, api
from odoo.tools.translate import _

class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """
    _name = 'account.move.reversal'
    _description = 'Account move reversal'

    date = fields.Date(string='Reversal date', default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string='Use Specific Journal', help='If empty, uses the journal of the journal entry to be reversed.')

    @api.multi
    def reverse_moves(self):
        ac_move_ids = self._context.get('active_ids', False)
        res = self.env['account.move'].browse(ac_move_ids).reverse_moves(self.date, self.journal_id or False)
        if res:
            return {
                'name': _('Reverse Moves'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'domain': [('id', 'in', res)],
            }
        return {'type': 'ir.actions.act_window_close'}
