from openerp import models, fields, api, _
from openerp.exceptions import Warning

class account_period_close(models.TransientModel):
    """
        close period
    """
    _name = "account.period.close"
    _description = "period close"

    sure = fields.Boolean(string='Check this box')

    @api.multi
    def data_save(self):
        """
        This function close period
         """
        mode = 'done'
        for form in self.read():
            if form['sure']:
                for id in self._context['active_ids']:
                    account_move_ids = self.env['account.move'].search([('period_id', '=', id), ('state', '=', "draft")])
                    if account_move_ids:
                        raise Warning(_('In order to close a period, you must first post related journal entries.'))

#                     cr.execute('update account_journal_period set state=%s where period_id=%s', (mode, id))
                    self._cr.execute('update account_period set state=%s where id=%s', (mode, id))
                    self.invalidate_cache()

        return {'type': 'ir.actions.act_window_close'}
