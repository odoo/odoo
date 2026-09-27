# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class CalendarAlarm_Manager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    @api.model
    def _send_reminder(self):
        """ Cron method, overridden here to send SMS reminders as well
        """
        super()._send_reminder()
        events_by_alarm = self._get_events_by_alarm_to_notify('sms')
        if not events_by_alarm:
            return

        all_events_ids = list({event_id for event_ids in events_by_alarm.values() for event_id in event_ids})
        for alarm_id, event_ids in events_by_alarm.items():
            alarm = self.env['calendar.alarm'].browse(alarm_id).with_prefetch(list(events_by_alarm.keys()))
            events = self.env['calendar.event'].browse(event_ids).with_prefetch(all_events_ids)
            events._do_sms_reminder(alarm)
            events._setup_event_recurrent_alarms(events_by_alarm)
