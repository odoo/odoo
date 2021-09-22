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
        alarms_by_event = self._get_events_by_alarm_to_notify('sms')
        if not alarms_by_event:
            return

        events = self.env['calendar.event'].browse(list(alarms_by_event.keys()))
        attendees = events.attendee_ids.filtered(lambda a: a.state != 'declined')
        for event_id in alarms_by_event.keys():
            event_alarms = attendees.event_id.alarm_ids.filtered(lambda alarm: alarm.id in alarms_by_event.get(event_id, []))
            for alarm in event_alarms:
                events.browse(event_id)._do_sms_reminder(alarm)
