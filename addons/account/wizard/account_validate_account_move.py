from openerp import models, fields, api, _
from openerp.exceptions import UserError


class validate_account_move(models.TransientModel):
    _name = "validate.account.move"
    _description = "Validate Account Move"

    journal_ids = fields.Many2many('account.journal', 'wizard_validate_account_move_journal', 'wizard_id', 'journal_id', string='Journal', required=True)
    date = fields.Date(string='Account Date', required=True, default=fields.Date.context_today)

    @api.multi
    def validate_move(self):
        moves = self.env['account.move'].search([('state', '=', 'draft'), ('journal_id', 'in', self.journal_ids.ids), ('date', '=', self.date)], order='date')
        if not moves:
            raise UserError(_('Specified journals do not have any account move entries in draft state for the specified periods.'))
        moves.button_validate()
        return {'type': 'ir.actions.act_window_close'}


class validate_account_move_lines(models.TransientModel):
    _name = "validate.account.move.lines"
    _description = "Validate Account Move Lines"

    @api.multi
    def validate_move_lines(self):
        context = self._context or {}
        move_ids = []
        data_line = self.env['account.move.line'].browse(context['active_ids'])
        for line in data_line:
            if line.move_id.state=='draft':
                move_ids.append(line.move_id)
        move_ids = list(set(move_ids))
        if not move_ids:
            raise UserError(_('Selected Entry Lines does not have any account move entries in draft state.'))
        move_ids.button_validate()
        return {'type': 'ir.actions.act_window_close'}
