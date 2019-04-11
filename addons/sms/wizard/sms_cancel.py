
from odoo import _, api, fields, models

class SMSCancel(models.TransientModel):
    _name = 'sms.cancel'
    _description = 'Dismiss notification for resend by model'

    model = fields.Char(string='Model')
    help_message = fields.Char(string='Help message', compute='_compute_help_message')

    @api.multi
    @api.depends('model')
    def _compute_help_message(self):
        for wizard in self:
            wizard.help_message = _("Are you sure you want to discard %s SMS delivery failures. You won't be able to re-send these SMS later!") % (wizard._context.get('unread_counter'))

    @api.multi
    def cancel_resend_action(self):
        author_id = self.env.user.id
        for wizard in self:
            self.env['sms.sms'].search([
                ('state', '=', 'error'),
                ('user_id', '=', author_id),
                ('message_id.model', '=', wizard.model)
            ])._cancel()
        return {'type': 'ir.actions.act_window_close'}
