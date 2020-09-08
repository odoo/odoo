from odoo import models, api, _
from odoo.exceptions import UserError


class ValidateAccountMove(models.TransientModel):
    _name = "validate.account.move"
    _description = "Validate Account Move"

    def validate_move(self):
        context = dict(self._context or {})
        if context.get("active_model") == "account.move":
            moves = self.env["account.move"].browse(context.get('active_ids'))
        elif context.get("active_model") == "account.journal":
            moves = self.env['account.move'].search([('journal_id', '=', context.get('active_id')),
                                                    ('state', '=', 'draft')]).filtered('line_ids')
        else:
            moves = self.env["account.move"]
        if not moves:
            raise UserError(_('There are no journal items in the draft state to post.'))
        moves.post()
        return {'type': 'ir.actions.act_window_close'}
