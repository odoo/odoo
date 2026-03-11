from odoo import api, fields, models


class CalendarEventMultiArchiveOrUnlinkWizard(models.TransientModel):
    _name = 'calendar.event.multi.archive.or.unlink.wizard'
    _description = 'Calendar Event Multi Archive Or Unlink Wizard'

    block_mail = fields.Boolean(default=False)
    calendar_event_ids = fields.Many2many(
        'calendar.event',
        # A name must be specified for the pivot table as the default one is too long.
        'calendar_event_multi_archive_or_unlink_wizard_rel',
        required=True)
    has_recurrent_events = fields.Boolean(compute='_compute_has_recurrent_events')
    requested_action = fields.Selection([
        ('archive', 'archive'),
        ('unlink', 'delete')
    ], default='archive', required=True)

    def _compute_has_recurrent_events(self):
        self.has_recurrent_events = bool(self.calendar_event_ids.recurrence_id)

    def action_archive(self):
        self.ensure_one()
        self.calendar_event_ids.write({'active': False})
        return self.env.context.get('next_action')

    def action_unlink(self):
        self.ensure_one()
        self.calendar_event_ids._unlink_with_sync_and_recurrence_check()
        return self.env.context.get('next_action')

    def action_send_mails_and_archive(self):
        self.ensure_one()
        self._send_mails()
        return self.action_archive()

    def action_send_mails_and_unlink(self):
        self.ensure_one()
        self._send_mails()
        return self.action_unlink()

    def _send_mails(self):
        self.ensure_one()
        now = fields.Datetime.now()
        events_to_notify = self.calendar_event_ids.filtered(
            lambda event: event.partner_ids != self.env.user.partner_id and event.start > now and not event.is_draft
        )
        self._send_mails_from_template(events_to_notify)

    @api.model
    def _send_mails_from_template(self, events_to_notify):
        """This method is meant to be overridden."""
        if template := self.env.ref('calendar.calendar_template_delete_event', raise_if_not_found=False):
            template.send_mail_batch(events_to_notify.ids)
