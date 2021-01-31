# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AlarmManager(models.AbstractModel):
    _name = 'calendar.alarm_manager'
    _description = 'Event Alarm Manager'

    def _get_next_potential_limit_alarm(self, alarm_type, seconds=None, partners=None):
        result = {}
        delta_request = """
            SELECT
                rel.calendar_event_id, max(alarm.duration_minutes) AS max_delta,min(alarm.duration_minutes) AS min_delta
            FROM
                calendar_alarm_calendar_event_rel AS rel
            LEFT JOIN calendar_alarm AS alarm ON alarm.id = rel.calendar_alarm_id
            WHERE alarm.alarm_type = %s
            GROUP BY rel.calendar_event_id
        """
        base_request = """
                    SELECT
                        cal.id,
                        cal.start - interval '1' minute  * calcul_delta.max_delta AS first_alarm,
                        CASE
                            WHEN cal.recurrency THEN rrule.until - interval '1' minute  * calcul_delta.min_delta
                            ELSE cal.stop - interval '1' minute  * calcul_delta.min_delta
                        END as last_alarm,
                        cal.start as first_event_date,
                        CASE
                            WHEN cal.recurrency THEN rrule.until
                            ELSE cal.stop
                        END as last_event_date,
                        calcul_delta.min_delta,
                        calcul_delta.max_delta,
                        rrule.rrule AS rule
                    FROM
                        calendar_event AS cal
                    RIGHT JOIN calcul_delta ON calcul_delta.calendar_event_id = cal.id
                    LEFT JOIN calendar_recurrence as rrule ON rrule.id = cal.recurrence_id
             """

        filter_user = """
                RIGHT JOIN calendar_event_res_partner_rel AS part_rel ON part_rel.calendar_event_id = cal.id
                    AND part_rel.res_partner_id IN %s
        """

        # Add filter on alarm type
        tuple_params = (alarm_type,)

        # Add filter on partner_id
        if partners:
            base_request += filter_user
            tuple_params += (tuple(partners.ids), )

        # Upper bound on first_alarm of requested events
        first_alarm_max_value = ""
        if seconds is None:
            # first alarm in the future + 3 minutes if there is one, now otherwise
            first_alarm_max_value = """
                COALESCE((SELECT MIN(cal.start - interval '1' minute  * calcul_delta.max_delta)
                FROM calendar_event cal
                RIGHT JOIN calcul_delta ON calcul_delta.calendar_event_id = cal.id
                WHERE cal.start - interval '1' minute  * calcul_delta.max_delta > now() at time zone 'utc'
            ) + interval '3' minute, now() at time zone 'utc')"""
        else:
            # now + given seconds
            first_alarm_max_value = "(now() at time zone 'utc' + interval '%s' second )"
            tuple_params += (seconds,)

        self._cr.execute("""
            WITH calcul_delta AS (%s)
            SELECT *
                FROM ( %s WHERE cal.active = True ) AS ALL_EVENTS
               WHERE ALL_EVENTS.first_alarm < %s
                 AND ALL_EVENTS.last_event_date > (now() at time zone 'utc')
        """ % (delta_request, base_request, first_alarm_max_value), tuple_params)

        for event_id, first_alarm, last_alarm, first_meeting, last_meeting, min_duration, max_duration, rule in self._cr.fetchall():
            result[event_id] = {
                'event_id': event_id,
                'first_alarm': first_alarm,
                'last_alarm': last_alarm,
                'first_meeting': first_meeting,
                'last_meeting': last_meeting,
                'min_duration': min_duration,
                'max_duration': max_duration,
                'rrule': rule
            }

        # determine accessible events
        events = self.env['calendar.event'].browse(result)
        result = {
            key: result[key]
            for key in set(events._filter_access_rules('read').ids)
        }
        return result

    def do_check_alarm_for_one_date(self, one_date, event, event_maxdelta, in_the_next_X_seconds, alarm_type, after=False, missing=False):
        """ Search for some alarms in the interval of time determined by some parameters (after, in_the_next_X_seconds, ...)
            :param one_date: date of the event to check (not the same that in the event browse if recurrent)
            :param event: Event browse record
            :param event_maxdelta: biggest duration from alarms for this event
            :param in_the_next_X_seconds: looking in the future (in seconds)
            :param after: if not False: will return alert if after this date (date as string - todo: change in master)
            :param missing: if not False: will return alert even if we are too late
            :param notif: Looking for type notification
            :param mail: looking for type email
        """
        result = []
        # TODO: remove event_maxdelta and if using it
        if one_date - timedelta(minutes=(missing * event_maxdelta)) < fields.Datetime.now() + timedelta(seconds=in_the_next_X_seconds):  # if an alarm is possible for this date
            for alarm in event.alarm_ids:
                if alarm.alarm_type == alarm_type and \
                    one_date - timedelta(minutes=(missing * alarm.duration_minutes)) < fields.Datetime.now() + timedelta(seconds=in_the_next_X_seconds) and \
                        (not after or one_date - timedelta(minutes=alarm.duration_minutes) > fields.Datetime.from_string(after)):
                    alert = {
                        'alarm_id': alarm.id,
                        'event_id': event.id,
                        'notify_at': one_date - timedelta(minutes=alarm.duration_minutes),
                    }
                    result.append(alert)
        return result

    @api.model
    def get_next_mail(self):
        return self._get_partner_next_mail(partners=None)

    @api.model
    def _get_partner_next_mail(self, partners=None):
        self = self.with_context(mail_notify_force_send=True)
        last_notif_mail = fields.Datetime.to_string(self.env.context.get('lastcall') or fields.Datetime.now())

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

        if cron.interval_type not in interval_to_second:
            _logger.error("Cron delay can not be computed !")
            return False

        cron_interval = cron.interval_number * interval_to_second[cron.interval_type]

        all_meetings = self._get_next_potential_limit_alarm('email', seconds=cron_interval, partners=partners)

        for meeting in self.env['calendar.event'].browse(all_meetings):
            max_delta = all_meetings[meeting.id]['max_duration']
            in_date_format = meeting.start
            last_found = self.do_check_alarm_for_one_date(in_date_format, meeting, max_delta, 0, 'email', after=last_notif_mail, missing=True)
            for alert in last_found:
                self.do_mail_reminder(alert)

    @api.model
    def get_next_notif(self):
        partner = self.env.user.partner_id
        all_notif = []

        if not partner:
            return []

        all_meetings = self._get_next_potential_limit_alarm('notification', partners=partner)
        time_limit = 3600 * 24  # return alarms of the next 24 hours
        for event_id in all_meetings:
            max_delta = all_meetings[event_id]['max_duration']
            meeting = self.env['calendar.event'].browse(event_id)
            in_date_format = fields.Datetime.from_string(meeting.start)
            last_found = self.do_check_alarm_for_one_date(in_date_format, meeting, max_delta, time_limit, 'notification', after=partner.calendar_last_notif_ack)
            if last_found:
                for alert in last_found:
                    all_notif.append(self.do_notif_reminder(alert))
        return all_notif

    def do_mail_reminder(self, alert):
        meeting = self.env['calendar.event'].browse(alert['event_id'])
        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])

        result = False
        if alarm.alarm_type == 'email':
            result = meeting.attendee_ids.filtered(lambda r: r.state != 'declined')._send_mail_to_attendees('calendar.calendar_template_meeting_reminder', force_send=True, ignore_recurrence=True)
        return result

    def do_notif_reminder(self, alert):
        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])
        meeting = self.env['calendar.event'].browse(alert['event_id'])

        if alarm.alarm_type == 'notification':
            message = meeting.display_time

            delta = alert['notify_at'] - fields.Datetime.now()
            delta = delta.seconds + delta.days * 3600 * 24

            return {
                'alarm_id': alarm.id,
                'event_id': meeting.id,
                'title': meeting.name,
                'message': message,
                'timer': delta,
                'notify_at': fields.Datetime.to_string(alert['notify_at']),
            }

    def _notify_next_alarm(self, partner_ids):
        """ Sends through the bus the next alarm of given partners """
        notifications = []
        users = self.env['res.users'].search([('partner_id', 'in', tuple(partner_ids))])
        for user in users:
            notif = self.with_user(user).get_next_notif()
            notifications.append([(self._cr.dbname, 'calendar.alarm', user.partner_id.id), notif])
        if len(notifications) > 0:
            self.env['bus.bus'].sendmany(notifications)
