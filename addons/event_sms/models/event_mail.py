# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventTypeMail(models.Model):
    _inherit = 'event.type.mail'

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')])

    def _selection_template_model(self):
        return super(EventTypeMail, self)._selection_template_model() + [('sms.template', 'SMS')]

    @api.depends('template_ref')
    def _compute_notification_type(self):
        sms_mails = self.filtered(lambda mail: mail.template_ref and mail.template_ref._name == 'sms.template')
        sms_mails.notification_type = 'sms'
        super(EventTypeMail, self - sms_mails)._compute_notification_type()


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')])

    @api.model
    def _selection_template_model(self):
        return super(EventMailScheduler, self)._selection_template_model() + [('sms.template', 'SMS')]

    @api.depends('template_ref')
    def _compute_notification_type(self):
        sms_mails = self.filtered(lambda mail: mail.template_ref and mail.template_ref._name == 'sms.template')
        sms_mails.notification_type = 'sms'
        super(EventMailScheduler, self - sms_mails)._compute_notification_type()

    def execute(self):
        for mail in self:
            now = fields.Datetime.now()
            if mail.interval_type != 'after_sub':
                # Do not send SMS if the communication was scheduled before the event but the event is over
                if not mail.mail_sent and (mail.interval_type != 'before_event' or mail.event_id.date_end > now) and mail.notification_type == 'sms' and mail.template_ref:
                    self.env['event.registration']._message_sms_schedule_mass(
                        template=mail.template_ref,
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
                record.registration_id._message_sms_schedule_mass(template=record.scheduler_id.template_ref, mass_keep_log=True)
                record.write({'mail_sent': True})
        return super(EventMailRegistration, self).execute()
