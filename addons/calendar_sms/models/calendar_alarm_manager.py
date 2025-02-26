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

        alarms = self.env['calendar.alarm'].browse(events_by_alarm.keys())
        for alarm in alarms:
            event_ids = events_by_alarm.get(alarm.id, [])
            events = self.env['calendar.event'].browse(event_ids)
            for event in events:
                event._do_sms_reminder(alarm)
