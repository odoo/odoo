from odoo import fields, models


class CalendarEventMultiCancelWizard(models.TransientModel):
    _name = 'calendar.event.multi.cancel.wizard'
    _description = 'Calendar Event Multi Cancel Wizard'

    def _default_cancel_wizard_ids(self):
        event_ids = self.env.context.get('active_model') == 'calendar.event' and self.env.context.get('active_ids') or []
        return [fields.Command.create({'calendar_event_id': event_id}) for event_id in event_ids]

    cancel_wizard_ids = fields.One2many('calendar.event.cancel.wizard', 'multi_cancel_wizard_id', default=_default_cancel_wizard_ids)
    is_user_admin = fields.Boolean(compute="_compute_is_user_admin")
    requested_action = fields.Selection([('cancel', 'cancel'), ('delete', 'delete')])

    def _compute_is_user_admin(self):
        for wizard in self:
            wizard.is_user_admin = self.env.user._is_admin()

    def action_cancel(self):
        self.cancel_wizard_ids.calendar_event_id.with_context(block_automatic_cancellation_email=True).write({'active': False})
        return self.env.context.get('next_action')

    def action_delete(self):
        self.cancel_wizard_ids.calendar_event_id._action_unlink()
        return self.env.context.get('next_action')

    def action_send_mails(self):
        now = fields.Datetime.now()
        self.env['mail.mail'].sudo().create([
            wizard._prepare_mail_values() for wizard in self.cancel_wizard_ids
            if wizard.calendar_event_id.partner_ids != self.env.user.partner_id
               and wizard.calendar_event_id.start > now
               and not wizard.calendar_event_id.is_draft
        ])

    def action_send_mails_and_cancel(self):
        self.action_send_mails()
        return self.action_cancel()

    def action_send_mails_and_delete(self):
        self.action_send_mails()
        return self.action_delete()
