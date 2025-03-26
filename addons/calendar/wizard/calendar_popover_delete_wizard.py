# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarPopoverDeleteWizard(models.TransientModel):
    _name = 'calendar.popover.delete.wizard'
    _inherit = ['mail.composer.mixin']
    _description = 'Calendar Popover Delete Wizard'


    record = fields.Many2one('calendar.event', 'Calendar Event')
    delete = fields.Selection([('one', 'Delete this event'), ('next', 'Delete this and following events'), ('all', 'Delete all the events')], default='one')
    recipient_ids = fields.Many2many(
        'res.partner',
        string="Recipients",
        compute='_compute_recipient_ids',
        readonly=False,
    )

    def close(self):
        # Return if there are multiple attendees or if the organizer's partner_id differs
        if self.record.attendees_count != 1 or self.record.user_id.partner_id != self.record.partner_ids:
            return self.record.action_unlink_event(self.record.partner_id.id, self.delete)
        if not self.record or not self.delete:
            pass
        elif self.delete == 'one':
            self.record.unlink()
        else:
            switch = {
                'next': 'future_events',
                'all': 'all_events'
            }
            self.record.action_mass_deletion(switch.get(self.delete, ''))

    @api.depends('record')
    def _compute_recipient_ids(self):
        """ Compute the recipients by combining the record's partner and message partners. """
        for wizard in self:
            wizard.recipient_ids = wizard.record.partner_id | wizard.record.attendee_ids.partner_id

    @api.depends('record')
    def _compute_subject(self):
        """ Compute the subject by rendering the template's subject field based on the record. """
        for wizard in self.filtered('template_id'):
            wizard.subject = wizard.template_id._render_field(
                'subject',
                [wizard.record.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard.record.id]

    @api.depends('record')
    def _compute_body(self):
        """ Compute the body by rendering the template's body HTML field based on the record. """
        for wizard in self.filtered('template_id'):
            wizard.body = wizard.template_id._render_field(
                'body_html',
                [wizard.record.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard.record.id]

    def action_delete(self):
        """
        Delete the event based on the specified deletion type.

        :return: Action URL to redirect to the calendar view
        """
        self.ensure_one()
        event = self.record
        deletion_type = self._context.get('default_recurrence')

        # Unlink recurrent events.
        if event.recurrency:
            if deletion_type in ['one', 'self_only']:
                event.unlink()
            elif deletion_type in ['next', 'all']:
                event.action_mass_deletion('future_events' if deletion_type == 'next' else 'all_events')
        else:
            event.unlink()

        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/odoo/calendar'
        }

    def action_send_mail_and_delete(self):
        """ Send email notification and delete the event based on the specified deletion type. """
        self.env.ref('calendar.calendar_template_delete_event').send_mail(
            self.record.id, email_layout_xmlid='mail.mail_notification_light', force_send=True
        )
        return self.action_delete()
