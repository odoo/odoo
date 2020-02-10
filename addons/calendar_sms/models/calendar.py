# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def _sms_get_default_partners(self):
        """ Method overridden from mail.thread (defined in the sms module).
            SMS text messages will be sent to attendees that haven't declined the event(s).
        """
        return self.mapped('attendee_ids').filtered(lambda att: att.state != 'declined').mapped('partner_id')

    def _do_sms_reminder(self, alarm):
        """ Send an SMS text reminder to attendees that haven't declined the event """
        for event in self:
            event._message_sms_with_template(
                template=alarm.sms_template_id,
                template_fallback=_("Event reminder: %(name)s, %(time)s.", name=event.name, time=event.display_time),
                partner_ids=self._sms_get_default_partners().ids,
                put_in_queue=False
            )

    def action_send_sms(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sms.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_composition_mode': 'mass',
                'default_res_model': 'res.partner',
                'default_res_ids': self.partner_ids.ids,
            },
        }

    def _get_trigger_alarm_types(self):
        return super()._get_trigger_alarm_types() + ['sms']


class CalendarAlarm(models.Model):
    _inherit = 'calendar.alarm'

    alarm_type = fields.Selection(selection_add=[
        ('sms', 'SMS Text Message')
    ], ondelete={'sms': 'set default'})
    sms_template_id = fields.Many2one('sms.template', string="SMS Template", domain=[('model', 'in', ['calendar.event', 'calendar.attendee'])],
        default=lambda self: self.env.ref('calendar_sms.sms_template_data_calendar_reminder', False),
        help="Template that would be used to send the reminder.")


class AlarmManager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    @api.model
    def _send_reminder(self):
        """ Cron method, overridden here to send SMS reminders as well
        """
        super()._send_reminder()
        alarms_by_event = self._get_events_to_notify(ttype='sms')
        if not alarms_by_event:
            return

        events = self.env['calendar.event'].browse(list(alarms_by_event.keys()))
        attendees = events.attendee_ids.filtered(lambda a: a.state != 'declined')
        for event_id in alarms_by_event.keys():
            event_alarms = attendees.event_id.alarm_ids.filtered(lambda alarm: alarm.id in alarms_by_event.get(event_id, []))
            for alarm in event_alarms:
                events.browse(event_id)._do_sms_reminder(alarm)
