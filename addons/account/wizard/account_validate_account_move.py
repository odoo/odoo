from odoo import models, fields, _
from odoo.exceptions import UserError


class ValidateAccountMove(models.TransientModel):
    _name = "validate.account.move"
    _description = "Validate Account Move"

    force_post = fields.Boolean(string="Force", help="Entries in the future are set to be auto-posted by default. Check this checkbox to post them now.")

    def validate_move(self):
        context = dict(self._context or {})
        moves = self.env['account.move'].browse(context.get('active_ids'))
        move_to_post = moves.filtered(lambda m: m.state == 'draft')
        if not move_to_post:
            raise UserError(_('There are no journal items in the draft state to post.'))
        move_to_post._post(not self.force_post)
        return {'type': 'ir.actions.act_window_close'}
