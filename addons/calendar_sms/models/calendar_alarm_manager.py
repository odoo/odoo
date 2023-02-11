# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AlarmManager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    @api.model
    def _send_reminder(self):
        """ Cron method, overridden here to send SMS reminders as well
        """
        super()._send_reminder()
        events_by_alarm = self._get_events_by_alarm_to_notify('sms')
        if not events_by_alarm:
            return

        event_ids = list(set(event_id for event_ids in events_by_alarm.values() for event_id in event_ids))
        events = self.env['calendar.event'].browse(event_ids)
        alarms = self.env['calendar.alarm'].browse(events_by_alarm.keys())
        for event in events:
            alarm = event.alarm_ids.filtered(lambda alarm : alarm.id in alarms.ids)
            event._do_sms_reminder(alarm)
