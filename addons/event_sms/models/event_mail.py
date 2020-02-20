# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventTypeMail(models.Model):
    _inherit = 'event.type.mail'

    notification_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'set default'})
    sms_template_id = fields.Many2one(
        'sms.template', string='SMS Template',
        domain=[('model', '=', 'event.registration')], ondelete='restrict',
        help='This field contains the template of the SMS that will be automatically sent')

    @api.model
    def _get_event_mail_fields_whitelist(self):
        return super(EventTypeMail, self)._get_event_mail_fields_whitelist() + ['sms_template_id']


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    notification_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'set default'})
    sms_template_id = fields.Many2one(
        'sms.template', string='SMS Template',
        domain=[('model', '=', 'event.registration')], ondelete='restrict',
        help='This field contains the template of the SMS that will be automatically sent')

    def execute(self):
        for mail in self:
            now = fields.Datetime.now()
            if mail.interval_type != 'after_sub':
                # Do not send SMS if the communication was scheduled before the event but the event is over
                if not mail.mail_sent and (mail.interval_type != 'before_event' or mail.event_id.date_end > now) and mail.notification_type == 'sms' and mail.sms_template_id:
                    self.env['event.registration']._message_sms_schedule_mass(
                        template=mail.sms_template_id,
                        active_domain=[('event_id', '=', mail.event_id.id), ('state', '!=', 'cancel')],
                        mass_keep_log=True
                    )
                    mail.write({'mail_sent': True})
        return super(EventMailScheduler, self).execute()


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def execute(self):
        for record in self:
            if record.registration_id.state in ['open', 'done'] and not record.mail_sent and record.scheduler_id.notification_type == 'sms':
                record.registration_id._message_sms_schedule_mass(template=record.scheduler_id.sms_template_id, mass_keep_log=True)
                record.write({'mail_sent': True})
        return super(EventMailRegistration, self).execute()
