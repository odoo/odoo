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
        for form in self:
            if form.sure:
                for id in self._context['active_ids']:
                    account_move = self.env['account.move'].search([('period_id', '=', id), ('state', '=', 'draft')], limit=1)
                    if account_move:
                        raise Warning(_('In order to close a period, you must first post related journal entries.'))

                    period = self.env['account.period'].browse(id)
                    period.state = 'done'

        return {'type': 'ir.actions.act_window_close'}
