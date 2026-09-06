# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.orm.decorators import readonly


class CalendarEventArchiveOrUnlinkWizard(models.TransientModel):
    _name = 'calendar.event.archive.or.unlink.wizard'
    _inherit = ['mail.composer.mixin']
    _description = 'Calendar Event Archive Or Unlink Wizard'

    calendar_event_id = fields.Many2one('calendar.event', 'Calendar Event', required=True)
    recipient_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        compute='_compute_recipient_ids',
        readonly=False,
    )
    recurrence_choice = fields.Selection([
        ('self_only', 'This event'),
        ('future_events', 'This and following events'),
        ('all_events', 'All the events'),
    ], default='self_only')
    requested_action = fields.Selection([
        ('archive', 'archive'),
        ('unlink', 'delete'),
    ], default='archive', required=True)
    template_id = fields.Many2one(compute='_compute_template_id')

    @api.depends('calendar_event_id')
    def _compute_recipient_ids(self):
        """ Compute the recipients by combining the record's partner and attendees partners. """
        for wizard in self:
            wizard.recipient_ids = wizard.calendar_event_id.partner_id | wizard.calendar_event_id.attendee_ids.partner_id

    @api.depends('calendar_event_id', 'template_id')
    def _compute_subject(self):
        """ Compute the subject by rendering the template's subject field based on the event. """
        for wizard in self.filtered('template_id'):
            wizard.subject = wizard.template_id._render_field(
                'subject',
                [wizard.calendar_event_id.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard.calendar_event_id.id]

    def _compute_template_id(self):
        self.template_id = self.env.ref('calendar.calendar_template_delete_event', raise_if_not_found=False)

    @api.depends('calendar_event_id', 'template_id')
    def _compute_body(self):
        """ Compute the body by rendering the template's body HTML field based on the event. """
        for wizard in self.filtered('template_id'):
            wizard.body = wizard.template_id._render_field(
                'body_html',
                [wizard.calendar_event_id.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard.calendar_event_id.id]

    def action_archive(self):
        self.ensure_one()
        self._get_calendar_events().write({'active': False})
        return self.env.context.get('next_action')

    def action_proceed_recurrence_choice(self):
        wizard_parameters = {
            'next_action': self.env.context.get('next_action'),
            'requested_action': self.requested_action,
        }
        # Return if there are multiple attendees or if the organizer's partner_id differs.
        if self.calendar_event_id.attendees_count != 1 or self.calendar_event_id.user_id.partner_id != self.calendar_event_id.partner_ids:
            return self.calendar_event_id.action_open_archive_or_unlink_wizard(
                recurrence_choice=self.recurrence_choice,
                **wizard_parameters
            )
        return self._get_calendar_events().action_open_archive_or_unlink_wizard(send_email=False, **wizard_parameters)

    def action_send_mail_and_archive(self):
        self.ensure_one()
        self._send_mail()
        return self.action_archive()

    def action_send_mail_and_unlink(self):
        """Send the composed email and delete the event based on the specified deletion type."""
        self.ensure_one()
        self._send_mail()
        return self.action_unlink()

    def action_unlink(self):
        """
        Delete the events specified with recurrence_choice field.

        :return: Client action to reload the page.
        """
        self.ensure_one()
        self.calendar_event_id._unlink_with_sync_and_recurrence_check(self.recurrence_choice)
        return self.env.context.get('next_action')

    def _get_calendar_events(self):
        if self.recurrence_choice in ['self_only', False]:
            return self.calendar_event_id
        elif self.recurrence_choice == 'future_events':
            return self.calendar_event_id.recurrence_id.calendar_event_ids.filtered(lambda event: event.start >= self.calendar_event_id.start)
        elif self.recurrence_choice == 'all_events':
            return self.calendar_event_id.recurrence_id.calendar_event_ids

    def _send_mail(self):
        self.ensure_one()
        self.calendar_event_id.sudo().message_notify(
            body=self.body,
            email_from=self.env.user.email_formatted,
            email_layout_xmlid='mail.mail_notification_light',
            partner_ids=self.recipient_ids.ids,
            subject=self.subject,
        )
