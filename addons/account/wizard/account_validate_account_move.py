from odoo import models, fields, _
from odoo.addons.account.models.exceptions import TaxClosingNonPostedDependingMovesError
from odoo.exceptions import UserError


class ValidateAccountMove(models.TransientModel):
    _name = "validate.account.move"
    _description = "Validate Account Move"

    force_post = fields.Boolean(string="Force", help="Entries in the future are set to be auto-posted by default. Check this checkbox to post them now.")

    def validate_move(self):
        if self._context.get('active_model') == 'account.move':
            domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'draft')]
        elif self._context.get('active_model') == 'account.journal':
            domain = [('journal_id', '=', self._context.get('active_id')), ('state', '=', 'draft')]
        else:
            raise UserError(_("Missing 'active_model' in context."))

        moves = self.env['account.move'].search(domain).filtered('line_ids')
        if not moves:
            raise UserError(_('There are no journal items in the draft state to post.'))
        if self.force_post:
            moves.auto_post = 'no'
        try:
            moves._post(not self.force_post)
        except TaxClosingNonPostedDependingMovesError as exception:
            return {
                "type": "ir.actions.client",
                "tag": "account_reports.redirect_action",
                "target": "new",
                "name": "Depending Action",
                "params": {
                    "depending_action": exception.args[0],
                },
                'context': {
                    'dialog_size': 'medium',
                },
            }
        return {'type': 'ir.actions.act_window_close'}
