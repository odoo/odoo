# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.orm.decorators import readonly


class CalendarEventUnlinkWizard(models.TransientModel):
    _name = 'calendar.event.unlink.wizard'
    _inherit = ['mail.composer.mixin']
    _description = 'Calendar Event Unlink Wizard'

    calendar_event_id = fields.Many2one('calendar.event', 'Calendar Event', required=True)
    recipient_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        compute='_compute_recipient_ids',
        readonly=False,
    )
    recurrence_choice = fields.Selection([
        ('self_only', 'Delete this event'),
        ('future_events', 'Delete this and following events'),
        ('all_events', 'Delete all the events'),
    ], default='self_only')
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

    def action_proceed_recurrence_choice(self):
        # Return if there are multiple attendees or if the organizer's partner_id differs.
        if self.calendar_event_id.attendees_count != 1 or self.calendar_event_id.user_id.partner_id != self.calendar_event_id.partner_ids:
            return self.calendar_event_id.action_open_unlink_wizard(self.env.context.get('next_action'), self.recurrence_choice)
        return self.action_unlink()

    def action_send_mail_and_unlink(self):
        """Send the composed email and delete the event based on the specified deletion type."""
        self.ensure_one()
        self.calendar_event_id.sudo().message_notify(
            body=self.body,
            email_from=self.env.user.email_formatted,
            email_layout_xmlid='mail.mail_notification_light',
            partner_ids=self.recipient_ids.ids,
            subject=self.subject,
        )
        return self.action_unlink()

    def action_unlink(self):
        """
        Delete the events specified with recurrence_choice field.

        :return: Client action to reload the page.
        """
        self.ensure_one()
        self.calendar_event_id._unlink_with_sync_and_recurrence_check(self.recurrence_choice)
        return self.env.context.get('next_action')
