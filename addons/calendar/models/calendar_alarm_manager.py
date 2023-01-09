# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)


class AlarmManager(models.AbstractModel):
    _name = 'calendar.alarm_manager'
    _description = 'Event Alarm Manager'

    def _get_next_potential_limit_alarm(self, alarm_type, seconds=None, partners=None):
        # flush models before making queries
        for model_name in ('calendar.alarm', 'calendar.event', 'calendar.recurrence'):
            self.env[model_name].flush_model()

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

        self.env.flush_all()
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
        past = one_date - timedelta(minutes=(missing * event_maxdelta))
        future = fields.Datetime.now() + timedelta(seconds=in_the_next_X_seconds)
        if future <= past:
            return result
        for alarm in event.alarm_ids:
            if alarm.alarm_type != alarm_type:
                continue
            past = one_date - timedelta(minutes=(missing * alarm.duration_minutes))
            if future <= past:
                continue
            if after and past <= fields.Datetime.from_string(after):
                continue
            result.append({
                'alarm_id': alarm.id,
                'event_id': event.id,
                'notify_at': one_date - timedelta(minutes=alarm.duration_minutes),
            })
        return result

    def _get_events_by_alarm_to_notify(self, alarm_type):
        """
        Get the events with an alarm of the given type between the cron
        last call and now.

        Please note that all new reminders created since the cron last
        call with an alarm prior to the cron last call are skipped by
        design. The attendees receive an invitation for any new event
        already.
        """
        self.env.cr.execute('''
            SELECT "alarm"."id", "event"."id"
              FROM "calendar_event" AS "event"
              JOIN "calendar_alarm_calendar_event_rel" AS "event_alarm_rel"
                ON "event"."id" = "event_alarm_rel"."calendar_event_id"
              JOIN "calendar_alarm" AS "alarm"
                ON "event_alarm_rel"."calendar_alarm_id" = "alarm"."id"
             WHERE (
                   "alarm"."alarm_type" = %s
               AND "event"."active"
               AND "event"."start" - CAST("alarm"."duration" || ' ' || "alarm"."interval" AS Interval) >= %s
               AND "event"."start" - CAST("alarm"."duration" || ' ' || "alarm"."interval" AS Interval) < now() at time zone 'utc'
             )''', [alarm_type, self.env.context['lastcall']])

        events_by_alarm = {}
        for alarm_id, event_id in self.env.cr.fetchall():
            events_by_alarm.setdefault(alarm_id, list()).append(event_id)
        return events_by_alarm

    @api.model
    def _send_reminder(self):
        # Executed via cron
        events_by_alarm = self._get_events_by_alarm_to_notify('email')
        if not events_by_alarm:
            return

        event_ids = list(set(event_id for event_ids in events_by_alarm.values() for event_id in event_ids))
        events = self.env['calendar.event'].browse(event_ids)
        attendees = events.attendee_ids.filtered(lambda a: a.state != 'declined')
        alarms = self.env['calendar.alarm'].browse(events_by_alarm.keys())
        for alarm in alarms:
            alarm_attendees = attendees.filtered(lambda attendee: attendee.event_id.id in events_by_alarm[alarm.id])
            alarm_attendees.with_context(
                mail_notify_force_send=True,
                calendar_template_ignore_recurrence=True
            )._send_mail_to_attendees(
                alarm.mail_template_id,
                force_send=True
            )

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

    def do_notif_reminder(self, alert):
        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])
        meeting = self.env['calendar.event'].browse(alert['event_id'])

        if alarm.alarm_type == 'notification':
            message = meeting.display_time
            if alarm.body:
                message += '<p>%s</p>' % plaintext2html(alarm.body)

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
            notif = self.with_user(user).with_context(allowed_company_ids=user.company_ids.ids).get_next_notif()
            notifications.append([user.partner_id, 'calendar.alarm', notif])
        if len(notifications) > 0:
            self.env['bus.bus']._sendmany(notifications)
