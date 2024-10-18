# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarPopoverDeleteWizard(models.TransientModel):
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
        return self.record.action_unlink_event(self.record.partner_id.id, self.delete)

    @api.depends('record')
    def _compute_recipient_ids(self):
        for wizard in self:
            wizard.recipient_ids = wizard.record.partner_id | wizard.record.message_partner_ids

    @api.depends('record')
    def _compute_subject(self):
        for wizard in self.filtered('template_id'):
            wizard.subject = wizard.template_id._render_field(
                'subject',
                [wizard.record.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard.record.id]

    @api.depends('record')
    def _compute_body(self):
        for wizard in self.filtered('template_id'):
            wizard.body = wizard.template_id._render_field(
                'body_html',
                [wizard.record.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard.record.id]

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_send_mail_and_delete(self):
        """
        Send email notification and delete the event based on the specified deletion type.

        :return: Action URL to redirect to the calendar view
        """
        self.ensure_one()
        event = self.record
        deletion_type = self._context.get('default_recurrence')

        # Send email notification
        self.env.ref('calendar.calendar_template_delete_event').send_mail(
            event.id, email_layout_xmlid='mail.mail_notification_light', force_send=True
        )

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
