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

    def _execute_event_based_for_registrations(self, registrations):
        if self.notification_type == "sms":
            self._send_sms(registrations)
        return super()._execute_event_based_for_registrations(registrations)

    def _send_sms(self, registrations):
        """ SMS action: send SMS to attendees """
        registrations._message_sms_schedule_mass(
            template=self.template_ref,
            mass_keep_log=True
        )

    def _template_model_by_notification_type(self):
        info = super()._template_model_by_notification_type()
        info["sms"] = "sms.template"
        return info
