# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarEventDeleteWizard(models.TransientModel):
    _name = 'calendar.event.delete.wizard'
    _inherit = ['mail.composer.mixin']
    _description = 'Calendar Event Delete Wizard'

    calendar_event_id = fields.Many2one('calendar.event', 'Calendar Event')
    delete = fields.Selection([('self_only', 'Delete this event'), ('future_events', 'Delete this and following events'), ('all_events', 'Delete all the events')], default='self_only')
    multi_delete_wizard_id = fields.Many2one('calendar.event.multi.delete.wizard', ondelete='cascade')
    recipient_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        compute='_compute_recipient_ids',
        readonly=False,
    )
    template_id = fields.Many2one('mail.template', default=lambda self: self.env.ref('calendar.calendar_template_delete_event', raise_if_not_found=False))

    def action_proceed_delete_choice(self):
        # Return if there are multiple attendees or if the organizer's partner_id differs
        if self.calendar_event_id.attendees_count != 1 or self.calendar_event_id.user_id.partner_id != self.calendar_event_id.partner_ids:
            return self.calendar_event_id.action_unlink(self.calendar_event_id.partner_id.id, self.env.context.get('next_action'), self.delete)
        return self.action_delete()

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

    def action_delete(self):
        """
        Delete the event based on the specified deletion type.

        :return: Client action to reload the page.
        """
        self.ensure_one()
        self.calendar_event_id._unlink_or_archive(self.delete)
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

    def action_send_mail_and_delete(self):
        """Send the composed email and delete the event based on the specified deletion type."""
        self.ensure_one()
        self.env['mail.mail'].sudo().create([self._prepare_mail_values()])
        return self.action_delete()
