from odoo import api, fields, models


class CalendarEventMultiUnlinkWizard(models.TransientModel):
    _name = 'calendar.event.multi.unlink.wizard'
    _description = 'Calendar Event Multi Unlink Wizard'

    calendar_event_ids = fields.Many2many('calendar.event', 'calendar_event_multi_unlink_wizard_rel', required=True)

    def action_unlink(self):
        self.ensure_one()
        self.calendar_event_ids._unlink_with_sync_and_recurrence_check()
        return self.env.context.get('next_action')

    def action_send_mails_and_unlink(self):
        self.ensure_one()
        now = fields.Datetime.now()
        events_to_notify = self.calendar_event_ids.filtered(
            lambda event: event.partner_ids != self.env.user.partner_id and event.start > now
        )
        self._send_mails_from_template(events_to_notify)
        return self.action_unlink()

    @api.model
    def _send_mails_from_template(self, events_to_notify):
        """This method is meant to be overridden."""
        if template := self.env.ref('calendar.calendar_template_delete_event', raise_if_not_found=False):
            template.send_mail_batch(events_to_notify.ids)
