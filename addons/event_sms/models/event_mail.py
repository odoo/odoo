# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventTypeMail(models.Model):
    _inherit = 'event.type.mail'

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')])
    template_ref = fields.Reference(ondelete={'sms.template': 'cascade'}, selection_add=[('sms.template', 'SMS')])

    def _compute_notification_type(self):
        super()._compute_notification_type()
        sms_schedulers = self.filtered(lambda scheduler: scheduler.template_ref and scheduler.template_ref._name == 'sms.template')
        sms_schedulers.notification_type = 'sms'


class EventMailScheduler(models.Model):
    _inherit = 'event.mail'

    notification_type = fields.Selection(selection_add=[('sms', 'SMS')])
    template_ref = fields.Reference(ondelete={'sms.template': 'cascade'}, selection_add=[('sms.template', 'SMS')])

    def _compute_notification_type(self):
        super()._compute_notification_type()
        sms_schedulers = self.filtered(lambda scheduler: scheduler.template_ref and scheduler.template_ref._name == 'sms.template')
        sms_schedulers.notification_type = 'sms'

    def execute(self):
        for scheduler in self:
            now = fields.Datetime.now()
            if scheduler.interval_type != 'after_sub' and scheduler.notification_type == 'sms':
                # before or after event -> one shot email
                if scheduler.mail_done:
                    continue
                # Do not send SMS if the communication was scheduled before the event but the event is over
                if scheduler.scheduled_date <= now and (scheduler.interval_type != 'before_event' or scheduler.event_id.date_end > now):
                    scheduler.event_id.registration_ids.filtered(
                        lambda registration: registration.state not in ('cancel', 'draft')
                    )._message_sms_schedule_mass(
                        template=scheduler.template_ref,
                        mass_keep_log=True
                    )
                    scheduler.update({
                        'mail_done': True,
                        'mail_count_done': scheduler.event_id.seats_taken,
                    })

        return super(EventMailScheduler, self).execute()
