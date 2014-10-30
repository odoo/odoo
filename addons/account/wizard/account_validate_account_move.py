from openerp import models, fields, api, _
from openerp.exceptions import Warning


class validate_account_move(models.TransientModel):
    _name = "validate.account.move"
    _description = "Validate Account Move"

    journal_ids = fields.Many2many('account.journal', 'wizard_validate_account_move_journal', 'wizard_id', 'journal_id', string='Journal', required=True)
    period_ids = fields.Many2many('account.period', 'wizard_validate_account_move_period', 'wizard_id', 'period_id', 'Period', string='Period', required=True, domain=[('state','<>','done')])

    @api.multi
    def validate_move(self):
        MoveObj = self.env['account.move']
        data = self.read()[0]
        ids_move = MoveObj.search([('state','=','draft'),('journal_id','in',tuple(data['journal_ids'])),('period_id','in',tuple(data['period_ids']))], order='date')
        if not ids_move:
            raise Warning(_('Specified journals do not have any account move entries in draft state for the specified periods.'))
        MoveObj.button_validate(ids_move.ids)
        return {'type': 'ir.actions.act_window_close'}


class validate_account_move_lines(models.TransientModel):
    _name = "validate.account.move.lines"
    _description = "Validate Account Move Lines"

    @api.multi
    def validate_move_lines(self):
        move_ids = []
        data_line = self.env['account.move.line'].browse(self._context['active_ids'])
        for line in data_line:
            if line.move_id.state=='draft':
                move_ids.append(line.move_id.id)
        move_ids = list(set(move_ids))
        if not move_ids:
            raise Warning(_('Selected Entry Lines does not have any account move entries in draft state.'))
        self.env['account.move'].button_validate(move_ids)
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

