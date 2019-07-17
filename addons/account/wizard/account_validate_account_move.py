from odoo import models, api, _
from odoo.exceptions import UserError


class ValidateAccountMove(models.TransientModel):
    _name = "validate.account.move"
    _description = "Validate Account Move"

    def validate_move(self):
        context = dict(self._context or {})
        moves = self.env['account.move'].browse(context.get('active_ids'))
        move_to_post = self.env['account.move']
        for move in moves:
            if move.state == 'draft':
                move_to_post += move
        if not move_to_post:
            raise UserError(_('There is no journal items in draft state to post.'))
        move_to_post.post()
        return {'type': 'ir.actions.act_window_close'}
