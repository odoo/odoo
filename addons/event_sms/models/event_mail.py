# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventTypeMail(models.Model):
    _inherit = 'event.type.mail'

    @api.model
    def _selection_template_model(self):
        return super(EventTypeMail, self)._selection_template_model() + [('sms.template', 'SMS')]

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')], ondelete={'sms': 'set default'})

    @api.depends('notification_type')
    def _compute_template_model_id(self):
        sms_model = self.env['ir.model']._get('sms.template')
        sms_mails = self.filtered(lambda mail: mail.notification_type == 'sms')
        sms_mails.template_model_id = sms_model
        super(EventTypeMail, self - sms_mails)._compute_template_model_id()


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    @api.model
    def _selection_template_model(self):
        return super(EventMailScheduler, self)._selection_template_model() + [('sms.template', 'SMS')]

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')], ondelete={'sms': 'set default'})

    @api.depends('notification_type')
    def _compute_template_model_id(self):
        sms_model = self.env['ir.model']._get('sms.template')
        sms_mails = self.filtered(lambda mail: mail.notification_type == 'sms')
        sms_mails.template_model_id = sms_model
        super(EventMailScheduler, self - sms_mails)._compute_template_model_id()

    def execute(self):
        for scheduler in self:
            now = fields.Datetime.now()
            if scheduler.interval_type != 'after_sub' and scheduler.notification_type == 'sms':
                # before or after event -> one shot email
                if scheduler.mail_done:
                    continue
                # no template -> ill configured, skip and avoid crash
                if not scheduler.template_ref:
                    continue
                # Do not send SMS if the communication was scheduled before the event but the event is over
                if scheduler.scheduled_date <= now and (scheduler.interval_type != 'before_event' or scheduler.event_id.date_end > now):
                    self.env['event.registration']._message_sms_schedule_mass(
                        template=scheduler.template_ref,
                        active_domain=[('event_id', '=', scheduler.event_id.id), ('state', '!=', 'cancel')],
                        mass_keep_log=True
                    )
                    scheduler.update({
                        'mail_done': True,
                        'mail_count_done': scheduler.event_id.seats_reserved + scheduler.event_id.seats_used,
                    })

        return super(EventMailScheduler, self).execute()


class EventMailRegistration(models.Model):
    _inherit = 'event.mail.registration'

    def execute(self):
        now = fields.Datetime.now()
        todo = self.filtered(lambda reg_mail:
            not reg_mail.mail_sent and \
            reg_mail.registration_id.state in ['open', 'done'] and \
            (reg_mail.scheduled_date and reg_mail.scheduled_date <= now) and \
            reg_mail.scheduler_id.notification_type == 'sms'
        )
        for reg_mail in todo:
            reg_mail.registration_id._message_sms_schedule_mass(
                template=reg_mail.scheduler_id.template_ref,
                mass_keep_log=True
            )
        todo.write({'mail_sent': True})

        return super(EventMailRegistration, self).execute()
