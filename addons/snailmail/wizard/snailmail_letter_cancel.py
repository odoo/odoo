
from odoo import _, api, fields, models

class SnailmailLetterCancel(models.TransientModel):
    _name = 'snailmail.letter.cancel'
    _description = 'Dismiss notification for resend by model'

    model = fields.Char(string='Model')
    help_message = fields.Char(string='Help message', compute='_compute_help_message')

    @api.depends('model')
    def _compute_help_message(self):
        for wizard in self:
            wizard.help_message = _("Are you sure you want to discard %s snailmail delivery failures? You won't be able to re-send these letters later!") % (wizard._context.get('unread_counter'))

    def cancel_resend_action(self):
        author_id = self.env.user.id
        for wizard in self:
            letters = self.env['snailmail.letter'].search([
                ('state', 'not in', ['sent', 'canceled', 'pending']),
                ('user_id', '=', author_id),
                ('model', '=', wizard.model)
            ])
            for letter in letters:
                letter.cancel()
        return {'type': 'ir.actions.act_window_close'}
