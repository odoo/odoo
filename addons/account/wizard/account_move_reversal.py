from openerp import models, fields, api


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
        self.env['account.move'].browse(ac_move_ids).reverse_moves(self.date, self.journal_id or False)
        return {'type': 'ir.actions.act_window_close'}
