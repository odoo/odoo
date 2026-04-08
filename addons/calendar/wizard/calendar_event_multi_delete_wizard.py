from odoo import fields, models


class CalendarEventMultiDeleteWizard(models.TransientModel):
    _name = 'calendar.event.multi.delete.wizard'
    _description = 'Calendar Event Multi Delete Wizard'

    def _default_delete_wizard_ids(self):
        event_ids = self.env.context.get('active_model') == 'calendar.event' and self.env.context.get('active_ids') or []
        return [fields.Command.create({'calendar_event_id': event_id}) for event_id in event_ids]

    delete_wizard_ids = fields.One2many('calendar.event.delete.wizard', 'multi_delete_wizard_id', default=_default_delete_wizard_ids)
    is_user_admin = fields.Boolean(compute="_compute_is_user_admin")

    def _compute_is_user_admin(self):
        for wizard in self:
            wizard.is_user_admin = self.env.user._is_admin()

    def action_delete(self):
        self.delete_wizard_ids.calendar_event_id._unlink_or_archive()
        return self.env.context.get('next_action')

    def action_send_mails_and_delete(self):
        now = fields.Datetime.now()
        self.env['mail.mail'].sudo().create([
            wizard._prepare_mail_values() for wizard in self.delete_wizard_ids
            if wizard.calendar_event_id.partner_ids != self.env.user.partner_id and wizard.calendar_event_id.start > now
        ])
        return self.action_delete()
