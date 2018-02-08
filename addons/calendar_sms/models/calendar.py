# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def _get_default_sms_recipients(self):
        """ Method overriden from mail.thread (defined in the sms module).
            SMS text messages will be sent to attendees that haven't declined the event(s).
        """
        return self.mapped('attendee_ids').filtered(lambda att: att.state != 'declined').mapped('partner_id')

    def _do_sms_reminder(self):
        """ Send an SMS text reminder to attendees that haven't declined the event """
        for event in self:
            sms_msg = _("Event reminder: %s on %s.") % (event.name, event.start_datetime or event.start_date)
            note_msg = _('SMS text message reminder sent !')
            event.message_post_send_sms(sms_msg, note_msg=note_msg)


class CalendarAlarm(models.Model):
    _inherit = 'calendar.alarm'

    type = fields.Selection(selection_add=[('sms', 'SMS Text Message')])


class AlarmManager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    @api.model
    def get_next_mail(self):
        """ Cron method, overriden here to send SMS reminders as well
        """
        result = super(AlarmManager, self).get_next_mail()
        now = fields.Datetime.now()
        last_sms_cron = self.env['ir.config_parameter'].get_param('calendar_sms.last_sms_cron', default=now)
        cron = self.env['ir.model.data'].get_object('calendar', 'ir_cron_scheduler_alarm')

        interval_to_second = {
            "weeks": 7 * 24 * 60 * 60,
            "days": 24 * 60 * 60,
            "hours": 60 * 60,
            "minutes": 60,
            "seconds": 1
        }

        cron_interval = cron.interval_number * interval_to_second[cron.interval_type]
        events_data = self.get_next_potential_limit_alarm('sms', seconds=cron_interval)

        for event in self.env['calendar.event'].browse(events_data):
            max_delta = events_data[event.id]['max_duration']

            if event.recurrency:
                found = False
                for event_start in event._get_recurrent_date_by_event():
                    event_start = event_start.replace(tzinfo=None)
                    last_found = self.do_check_alarm_for_one_date(event_start, event, max_delta, 0, 'sms', after=last_sms_cron, missing=True)
                    for alert in last_found:
                        event.browse(alert['event_id'])._do_sms_reminder()
                        found = True
                    if found and not last_found:  # if the precedent event had an alarm but not this one, we can stop the search for this event
                        break
            else:
                event_start = fields.Datetime.from_string(event.start)
                for alert in self.do_check_alarm_for_one_date(event_start, event, max_delta, 0, 'sms', after=last_sms_cron, missing=True):
                    event.browse(alert['event_id'])._do_sms_reminder()
        self.env['ir.config_parameter'].set_param('calendar_sms.last_sms_cron', now)
        return result
