# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEventCancelWizard(models.TransientModel):
    _name = 'calendar.event.cancel.wizard'
    _inherit = ['mail.composer.mixin']
    _description = 'Calendar Event Cancel Wizard'

    calendar_event_id = fields.Many2one('calendar.event', 'Calendar Event')
    multi_cancel_wizard_id = fields.Many2one('calendar.event.multi.cancel.wizard', ondelete='cascade')
    recipient_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        compute='_compute_recipient_ids',
        readonly=False,
    )
    recurrence_choice = fields.Selection([('self_only', 'This event'), ('future_events', 'This and following events'), ('all_events', 'All the events')], default='self_only')
    requested_action = fields.Selection([('cancel', 'cancel'), ('delete', 'delete')])
    template_id = fields.Many2one('mail.template', default=lambda self: self.env.ref('calendar.calendar_template_delete_event', raise_if_not_found=False))

    def action_proceed_recurrence_choice(self):
        # Return if there are multiple attendees or if the organizer's partner_id differs
        cancellation_parameters = {
            'attendee_id': self.calendar_event_id.partner_id.id,
            'next_action': self.env.context.get('next_action'),
            'requested_action': self.requested_action,
        }
        if self.calendar_event_id.attendees_count != 1 or self.calendar_event_id.user_id.partner_id != self.calendar_event_id.partner_ids:
            return self.calendar_event_id.action_open_cancel_wizard(recurrence_choice=self.recurrence_choice, **cancellation_parameters)
        return self._get_calendar_events().action_open_cancel_wizard(send_email=False, **cancellation_parameters)

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

    def _get_calendar_events(self):
        calendar_events = self.env['calendar.event']
        if self.recurrence_choice in ['self_only', False]:
            calendar_events += self.calendar_event_id
        elif self.recurrence_choice == 'future_events':
            calendar_events += self.calendar_event_id.recurrence_id.calendar_event_ids.filtered(lambda event: event.start >= self.calendar_event_id.start)
        elif self.recurrence_choice == 'all_events':
            calendar_events += self.calendar_event_id.recurrence_id.calendar_event_ids
        return calendar_events

    def action_cancel(self):
        self.ensure_one()
        self._get_calendar_events().with_context(block_automatic_cancellation_email=True).write({'active': False})
        return self.env.context.get('next_action')

    def action_delete(self):
        """
        Delete the event based on the specified deletion type.

        :return: Client action to reload the page.
        """
        self.ensure_one()
        self.calendar_event_id._action_unlink(self.recurrence_choice)
        return self.env.context.get('next_action')

    def _prepare_mail_values(self):
        self.ensure_one()
        return {
            'auto_delete': True,
            'body_html': self.body,
            'email_from': self.env.user.email_formatted,
            'recipient_ids': self.recipient_ids.ids,
            'subject': self.subject,
        }

    def action_send_mail(self):
        self.ensure_one()
        self.env['mail.mail'].sudo().create([self._prepare_mail_values()])

    def action_send_mail_and_cancel(self):
        self.ensure_one()
        self.action_send_mail()
        return self.action_cancel()

    def action_send_mail_and_delete(self):
        """Send the composed email and delete the event based on the specified deletion type."""
        self.ensure_one()
        self.action_send_mail()
        return self.action_delete()
