# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CalendarAlarmManager(models.AbstractModel):
    _name = 'calendar.alarm_manager'

    def get_next_potential_limit_alarm(self, seconds, notif=True, mail=True, partner_id=None):
        res = {}
        base_request = """
                    SELECT
                        cal.id,
                        cal.start - interval '1' minute  * calcul_delta.max_delta AS first_alarm,
                        CASE
                            WHEN cal.recurrency THEN cal.final_date - interval '1' minute  * calcul_delta.min_delta
                            ELSE cal.stop - interval '1' minute  * calcul_delta.min_delta
                        END as last_alarm,
                        cal.start as first_event_date,
                        CASE
                            WHEN cal.recurrency THEN cal.final_date
                            ELSE cal.stop
                        END as last_event_date,
                        calcul_delta.min_delta,
                        calcul_delta.max_delta,
                        cal.rrule AS rule
                    FROM
                        calendar_event AS cal
                        RIGHT JOIN
                            (
                                SELECT
                                    rel.calendar_event_id, max(alarm.duration_minutes) AS max_delta,min(alarm.duration_minutes) AS min_delta
                                FROM
                                    calendar_alarm_calendar_event_rel AS rel
                                        LEFT JOIN calendar_alarm AS alarm ON alarm.id = rel.calendar_alarm_id
                                WHERE alarm.type in %s
                                GROUP BY rel.calendar_event_id
                            ) AS calcul_delta ON calcul_delta.calendar_event_id = cal.id
             """

        filter_user = """
                RIGHT JOIN calendar_event_res_partner_rel AS part_rel ON part_rel.calendar_event_id = cal.id
                    AND part_rel.res_partner_id = %s
        """

        #Add filter on type
        type_to_read = ()
        if notif:
            type_to_read += ('notification',)
        if mail:
            type_to_read += ('email',)

        tuple_params = (type_to_read,)

        # ADD FILTER ON PARTNER_ID
        if partner_id:
            base_request += filter_user
            tuple_params += (partner_id, )

        #Add filter on hours
        tuple_params += (seconds,)

        self.env.cr.execute("""SELECT *
                        FROM ( %s WHERE cal.active = True ) AS ALL_EVENTS
                       WHERE ALL_EVENTS.first_alarm < (now() at time zone 'utc' + interval '%%s' second )
                         AND ALL_EVENTS.last_event_date > (now() at time zone 'utc')
                   """ % base_request, tuple_params)

        for event_id, first_alarm, last_alarm, first_meeting, last_meeting, min_duration, max_duration, rule in self.env.cr.fetchall():
            res[event_id] = {
                'event_id': event_id,
                'first_alarm': first_alarm,
                'last_alarm': last_alarm,
                'first_meeting': first_meeting,
                'last_meeting': last_meeting,
                'min_duration': min_duration,
                'max_duration': max_duration,
                'rrule': rule
            }

        return res

    def do_check_alarm_for_one_date(self, one_date, event, event_maxdelta, in_the_next_X_seconds, after=False, notif=True, mail=True, missing=False):
        # one_date: date of the event to check (not the same that in the event browse if recurrent)
        # event: Event browse record
        # event_maxdelta: biggest duration from alarms for this event
        # in_the_next_X_seconds: looking in the future (in seconds)
        # after: if not False: will return alert if after this date (date as string - todo: change in master)
        # missing: if not False: will return alert even if we are too late
        # notif: Looking for type notification
        # mail: looking for type email

        res = []

        # TODO: replace notif and email in master by alarm_type + remove event_maxdelta and if using it
        alarm_type = []
        if notif:
            alarm_type.append('notification')
        if mail:
            alarm_type.append('email')

        if one_date - timedelta(minutes=(missing and 0 or event_maxdelta)) < datetime.now() + timedelta(seconds=in_the_next_X_seconds):  # if an alarm is possible for this date
            for alarm in event.alarm_ids:
                if alarm.type in alarm_type and \
                    one_date - timedelta(minutes=(missing and 0 or alarm.duration_minutes)) < datetime.now() + timedelta(seconds=in_the_next_X_seconds) and \
                        (not after or one_date - timedelta(minutes=alarm.duration_minutes) > fields.Datetime.from_string(after)):
                        alert = {
                            'alarm': alarm,
                            'event': event,
                            'notify_at': one_date - timedelta(minutes=alarm.duration_minutes),
                        }
                        res.append(alert)
        return res

    @api.model
    def get_next_mail(self):
        now = fields.Datetime.now()
        IrConfigParameter = self.env['ir.config_parameter']
        last_notif_mail = IrConfigParameter.sudo().get_param('calendar.last_notif_mail', now)

        cron = self.env.ref('calendar.ir_cron_scheduler_alarm', raise_if_not_found=False)
        if not cron:
            _logger.error("Cron for " + self._name + " can not be identified !")
            return False

        interval_to_second = {
            "weeks": 7 * 24 * 60 * 60,
            "days": 24 * 60 * 60,
            "hours": 60 * 60,
            "minutes": 60,
            "seconds": 1
        }

        if cron.interval_type not in interval_to_second.keys():
            _logger.error("Cron delay can not be computed !")
            return False

        cron_interval = cron.interval_number * interval_to_second[cron.interval_type]

        all_events = self.get_next_potential_limit_alarm(cron_interval, notif=False)

        for curEvent in self.env['calendar.event'].browse(all_events.keys()):
            max_delta = all_events[curEvent.id]['max_duration']

            if curEvent.recurrency:
                at_least_one = False
                last_found = False
                for one_date in curEvent.get_recurrent_date_by_event():
                    in_date_format = one_date.replace(tzinfo=None)
                    last_found = self.do_check_alarm_for_one_date(in_date_format, curEvent, max_delta, 0, after=last_notif_mail, notif=False, missing=True)
                    for alert in last_found:
                        self.do_mail_reminder(alert)
                        at_least_one = True  # if it's the first alarm for this recurrent event
                    if at_least_one and not last_found:  # if the precedent event had an alarm but not this one, we can stop the search for this event
                        break
            else:
                in_date_format = fields.Datetime.from_string(curEvent.start)
                last_found = self.do_check_alarm_for_one_date(in_date_format, curEvent, max_delta, 0, after=last_notif_mail, notif=False, missing=True)
                for alert in last_found:
                    self.do_mail_reminder(alert)
        IrConfigParameter.sudo().set_param('calendar.last_notif_mail', now)

    @api.model
    def get_next_notif(self):
        ajax_check_every_seconds = 300
        partner = self.env.user.partner_id
        cal_last_notif_ack = self.env.user.calendar_last_notif_ack
        all_notif = []

        if not partner:
            return []

        all_events = self.get_next_potential_limit_alarm(ajax_check_every_seconds, partner_id=partner.id, mail=False)

        for event in all_events:  # .values()
            max_delta = all_events[event]['max_duration']
            curEvent = self.env['calendar.event'].browse(event)
            if curEvent.recurrency:
                bFound = False
                LastFound = False
                for one_date in curEvent.get_recurrent_date_by_event():
                    in_date_format = one_date.replace(tzinfo=None)
                    LastFound = self.do_check_alarm_for_one_date(in_date_format, curEvent, max_delta, ajax_check_every_seconds, after=cal_last_notif_ack, mail=False)
                    if LastFound:
                        for alert in LastFound:
                            all_notif.append(self.do_notif_reminder(alert))
                        if not bFound:  # if it's the first alarm for this recurrent event
                            bFound = True
                    if bFound and not LastFound:  # if the precedent event had alarm but not this one, we can stop the search fot this event
                        break
            else:
                in_date_format = fields.Datetime.from_string(curEvent.start)
                LastFound = self.do_check_alarm_for_one_date(in_date_format, curEvent, max_delta, ajax_check_every_seconds, after=cal_last_notif_ack, mail=False)
                if LastFound:
                    for alert in LastFound:
                        all_notif.append(self.do_notif_reminder(alert))
        return all_notif

    @api.multi
    def do_mail_reminder(self, alert):
        res = False
        if alert['alarm'].type == 'email':
            res = alert['event'].attendee_ids._send_mail_to_attendees(
                email_from=alert['event'].user_id.partner_id.email,
                template_xmlid='calendar_template_meeting_reminder',
                force=True
            )
        return res

    @api.multi
    def do_notif_reminder(self, alert):
        if alert['alarm'].type == 'notification':
            delta = alert['notify_at'] - datetime.now()
            delta = delta.seconds + delta.days * 3600 * 24

            return {
                'event_id': alert['event'].id,
                'title': alert['event'].name,
                'message': alert['event'].display_time,
                'timer': delta,
                'notify_at': fields.Datetime.to_string(alert['notify_at'])
            }


class CalendarAlarm(models.Model):
    _name = 'calendar.alarm'
    _description = 'Event alarm'

    _interval_selection = {'minutes': 'Minute(s)', 'hours': 'Hour(s)', 'days': 'Day(s)'}

    name = fields.Char(required=True)
    type = fields.Selection([('notification', 'Notification'), ('email', 'Email')], default='email', required=True)
    duration = fields.Integer('Amount', default=1, required=True)
    interval = fields.Selection(list(_interval_selection.iteritems()), string='Unit', default='hours', required=True)
    duration_minutes = fields.Integer(compute='_get_duration', string='Duration in minutes', store=True, help="Duration in minutes")

    @api.depends('interval', 'duration')
    def _get_duration(self):
        for alarm in self:
            if alarm.interval == "minutes":
                alarm.duration_minutes = alarm.duration
            elif alarm.interval == "hours":
                alarm.duration_minutes = alarm.duration * 60
            elif alarm.interval == "days":
                alarm.duration_minutes = alarm.duration * 60 * 24
            else:
                alarm.duration_minutes = 0

    @api.onchange('duration', 'interval')
    def onchange_duration_interval(self):
        self.display_interval = self._interval_selection.get(self.interval, '')
        self.name = str(self.duration) + ' ' + self.display_interval

    @api.model
    def _update_cron(self):
        cron = self.env.ref('calendar.ir_cron_scheduler_alarm', raise_if_not_found=False)
        return cron and cron.toggle(model=self._name, domain=[('type', '=', 'email')])

    @api.model
    def create(self, values):
        res = super(CalendarAlarm, self).create(values)
        self._update_cron()
        return res

    @api.multi
    def write(self, values):
        res = super(CalendarAlarm, self).write(values)
        self._update_cron()
        return res

    @api.multi
    def unlink(self):
        res = super(CalendarAlarm, self).unlink()
        self._update_cron()
        return res
