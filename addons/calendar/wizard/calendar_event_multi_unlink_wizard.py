from odoo import fields, models


class CalendarEventMultiUnlinkWizard(models.TransientModel):
    _name = 'calendar.event.multi.unlink.wizard'
    _description = 'Calendar Event Multi Unlink Wizard'

    def _default_unlink_wizard_ids(self):
        event_ids = self.env.context.get('active_model') == 'calendar.event' and self.env.context.get('active_ids') or []
        return [fields.Command.create({'calendar_event_id': event_id}) for event_id in event_ids]

    unlink_wizard_ids = fields.One2many('calendar.event.unlink.wizard', 'multi_unlink_wizard_id', default=_default_unlink_wizard_ids)
    is_user_admin = fields.Boolean(compute="_compute_is_user_admin")

    def _compute_is_user_admin(self):
        for wizard in self:
            wizard.is_user_admin = self.env.user._is_admin()

    def action_unlink(self):
        self.unlink_wizard_ids.calendar_event_id._action_unlink()
        return self.env.context.get('next_action')

    def action_send_mails_and_unlink(self):
        now = fields.Datetime.now()
        self.env['mail.mail'].sudo().create([
            wizard._prepare_mail_values() for wizard in self.unlink_wizard_ids
            if wizard.calendar_event_id.partner_ids != self.env.user.partner_id and wizard.calendar_event_id.start > now
        ]).send_after_commit()
        return self.action_unlink()
