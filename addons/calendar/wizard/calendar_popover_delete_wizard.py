# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarProviderConfig(models.TransientModel):
    _name = 'calendar.popover.delete.wizard'
    _inherit = 'mail.composer.mixin'
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
        return self.record.unlink_event(self.record.partner_id.id, self.delete)

    @api.depends('record')
    def _compute_recipient_ids(self):
        for wizard in self:
            wizard.recipient_ids = wizard.record.partner_id | wizard.record.message_partner_ids

    @api.depends('record')
    def _compute_subject(self):
        for wizard_subject in self.filtered('template_id'):
            wizard_subject.subject = wizard_subject.template_id._render_field(
                'subject',
                [wizard_subject.record.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard_subject.record.id]

    @api.depends('record')
    def _compute_body(self):
        for wizard_body in self.filtered('template_id'):
            wizard_body.body = wizard_body.template_id._render_field(
                'body_html',
                [wizard_body.record.id],
                compute_lang=True,
                options={'post_process': True},
            )[wizard_body.record.id]

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
        template = self.env.ref('calendar.calendar_template_delete_event')
        template.send_mail(event.id, email_layout_xmlid='mail.mail_notification_light', force_send=True)

        if event.recurrency:
            if not event or not deletion_type:
                pass
            elif deletion_type in ['one', 'self_only']:
                event.unlink()
            else:
                deletion_options = {
                    'next': 'future_events',
                    'all': 'all_events'
                }
                deletion_method = deletion_options.get(deletion_type, '')
                event.action_mass_deletion(deletion_method)
        else:
            event.unlink()
        return {'type': 'ir.actions.act_url', 'target': 'self', 'url': '/odoo/calendar'}
