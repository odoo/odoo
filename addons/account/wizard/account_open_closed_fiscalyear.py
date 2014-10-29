from openerp import models, api, _
from openerp.exceptions import Warning

class account_open_closed_fiscalyear(models.TransientModel):
    _name = "account.open.closed.fiscalyear"
    _description = "Choose Fiscal Year"

    fyear_id = fields.Many2one('account.fiscalyear', string='Fiscal Year', required=True, 
        help='Select Fiscal Year which you want to remove entries for its End of year entries journal')

    @api.multi
    def remove_entries(self):
        period_journal = self.fyear_id.end_journal_id or False
        if not period_journal:
            raise Warning(_("You have to set the 'End  of Year Entries Journal' for this Fiscal Year which is set after generating opening entries from 'Generate Opening Entries'."))

        ids_move = self.env['account.move'].search([('journal_id','=',period_journal.journal_id.id),('period_id','=',period_journal.period_id.id)])
        if ids_move:
            self._cr.execute('delete from account_move where id IN %s', (tuple(ids_move.ids),))
            self.invalidate_cache()
        return {'type': 'ir.actions.act_window_close'}

