# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _


class Meeting(models.Model):
    _name = 'calendar.event'
    _inherit = ['calendar.event', 'google.calendar.sync']

    google_id = fields.Char(
        'Google Calendar Event Id', compute='_compute_google_id', store=True, readonly=False)

    @api.depends('recurrence_id.google_id')
    def _compute_google_id(self):
        # google ids of recurring events are built from the recurrence id and the
        # original starting time in the recurrence.
        # The `start` field does not appear in the dependencies on purpose!
        # Event if the event is moved, the google_id remains the same.
        for event in self:
            google_recurrence_id = event.recurrence_id._get_event_google_id(event)
            if not event.google_id and google_recurrence_id:
                event.google_id = google_recurrence_id
            elif not event.google_id:
                event.google_id = False

    @api.model
    def _get_google_synced_fields(self):
        return {'name', 'description', 'allday', 'start', 'date_end', 'stop',
                'attendee_ids', 'alarm_ids', 'location', 'privacy', 'active'}

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([
            dict(vals, need_sync=False) if vals.get('recurrence_id') or vals.get('recurrency') else vals
            for vals in vals_list
        ])

    def write(self, values):
        recurrence_update_setting = values.get('recurrence_update')
        if recurrence_update_setting in ('all_events', 'future_events') and len(self) == 1:
            values = dict(values, need_sync=False)
        res = super().write(values)
        if recurrence_update_setting in ('all_events',) and len(self) == 1 and values.keys() & self._get_google_synced_fields():
            self.recurrence_id.need_sync = True
        return res

    def _get_sync_domain(self):
        return [('partner_ids.user_ids', 'in', self.env.user.id)]

    @api.model
    def _odoo_values(self, google_event, default_reminders=()):
        if google_event.is_cancelled():
            return {'active': False}

        # default_reminders is never () it is set to google's default reminder (30 min before)
        # we need to check 'useDefault' for the event to determine if we have to use google's
        # default reminder or not
        reminder_command = google_event.reminders.get('overrides')
        if not reminder_command:
            reminder_command = google_event.reminders.get('useDefault') and default_reminders or ()
        alarm_commands = self._odoo_reminders_commands(reminder_command)
        attendee_commands, partner_commands = self._odoo_attendee_commands(google_event)
        values = {
            'name': google_event.summary or _("(No title)"),
            'description': google_event.description,
            'location': google_event.location,
            'user_id': google_event.owner(self.env).id,
            'privacy': google_event.visibility or self.default_get(['privacy'])['privacy'],
            'attendee_ids': attendee_commands,
            'partner_ids': partner_commands,
            'alarm_ids': alarm_commands,
            'recurrency': google_event.is_recurrent()
        }

        if not google_event.is_recurrence():
            values['google_id'] = google_event.id
        if google_event.start.get('dateTime'):
            # starting from python3.7, use the new [datetime, date].fromisoformat method
            start = parse(google_event.start.get('dateTime')).astimezone(pytz.utc).replace(tzinfo=None)
            stop = parse(google_event.end.get('dateTime')).astimezone(pytz.utc).replace(tzinfo=None)
            values['allday'] = False
        else:
            start = parse(google_event.start.get('date'))
            stop = parse(google_event.end.get('date')) - relativedelta(days=1)
            stop = max(start, stop)  # For the cases that start date and end date were the same
            values['allday'] = True
        values['start'] = start
        values['stop'] = stop
        return values

    @api.model
    def _odoo_attendee_commands(self, google_event):
        attendee_commands = []
        partner_commands = []
        google_attendees = google_event.attendees or []
        if len(google_attendees) == 0 and google_event.organizer and google_event.organizer.get('self', False):
            user = google_event.owner(self.env)
            google_attendees += [{
                'email': user.partner_id.email,
                'status': {'response': 'accepted'},
            }]
        emails = [a.get('email') for a in google_attendees]
        existing_attendees = self.env['calendar.attendee']
        if google_event.exists(self.env):
            existing_attendees = self.browse(google_event.odoo_id(self.env)).attendee_ids
        attendees_by_emails = {tools.email_normalize(a.email): a for a in existing_attendees}
        for attendee in google_attendees:
            email = attendee.get('email')

            if email in attendees_by_emails:
                # Update existing attendees
                attendee_commands += [(1, attendees_by_emails[email].id, {'state': attendee.get('responseStatus')})]
            else:
                # Create new attendees
                partner = self.env.user.partner_id if attendee.get('self') else self.env['res.partner'].find_or_create(attendee.get('email'))
                attendee_commands += [(0, 0, {'state': attendee.get('responseStatus'), 'partner_id': partner.id})]
                partner_commands += [(4, partner.id)]
                if attendee.get('displayName') and not partner.name:
                    partner.name = attendee.get('displayName')
        for odoo_attendee in attendees_by_emails.values():
            # Remove old attendees
            if tools.email_normalize(odoo_attendee.email) not in emails:
                attendee_commands += [(2, odoo_attendee.id)]
                partner_commands += [(3, odoo_attendee.partner_id.id)]
        return attendee_commands, partner_commands

    @api.model
    def _odoo_reminders_commands(self, reminders=()):
        commands = []
        for reminder in reminders:
            alarm_type = 'email' if reminder.get('method') == 'email' else 'notification'
            alarm_type_label = _("Email") if alarm_type == 'email' else _("Notification")

            minutes = reminder.get('minutes', 0)
            alarm = self.env['calendar.alarm'].search([
                ('alarm_type', '=', alarm_type),
                ('duration_minutes', '=', minutes)
            ], limit=1)
            if alarm:
                commands += [(4, alarm.id)]
            else:
                if minutes % (60*24) == 0:
                    interval = 'days'
                    duration = minutes / 60 / 24
                    name = _(
                        "%(reminder_type)s - %(duration)s Days",
                        reminder_type=alarm_type_label,
                        duration=duration,
                    )
                elif minutes % 60 == 0:
                    interval = 'hours'
                    duration = minutes / 60
                    name = _(
                        "%(reminder_type)s - %(duration)s Hours",
                        reminder_type=alarm_type_label,
                        duration=duration,
                    )
                else:
                    interval = 'minutes'
                    duration = minutes
                    name = _(
                        "%(reminder_type)s - %(duration)s Minutes",
                        reminder_type=alarm_type_label,
                        duration=duration,
                    )
                commands += [(0, 0, {'duration': duration, 'interval': interval, 'name': name, 'alarm_type': alarm_type})]
        return commands

    def _google_values(self):
        if self.allday:
            start = {'date': self.start_date.isoformat()}
            end = {'date': (self.stop_date + relativedelta(days=1)).isoformat()}
        else:
            start = {'dateTime': pytz.utc.localize(self.start).isoformat()}
            end = {'dateTime': pytz.utc.localize(self.stop).isoformat()}

        reminders = [{
            'method': "email" if alarm.alarm_type == "email" else "popup",
            'minutes': alarm.duration_minutes
        } for alarm in self.alarm_ids]
        attendee_ids = self.attendee_ids.filtered(lambda a: a.partner_id not in self.user_id.partner_id)
        values = {
            'id': self.google_id,
            'start': start,
            'end': end,
            'summary': self.name,
            'description': self.description or '',
            'location': self.location or '',
            'guestsCanModify': True,
            'organizer': {'email': self.user_id.email, 'self': self.user_id == self.env.user},
            'attendees': [{
                'email': attendee.email,
                'responseStatus': attendee.state or 'needsAction',
            } for attendee in self.attendee_ids if attendee.email],
            'extendedProperties': {
                'shared': {
                    '%s_odoo_id' % self.env.cr.dbname: self.id,
                },
            },
            'reminders': {
                'overrides': reminders,
                'useDefault': False,
            }
        }
        if self.privacy:
            values['visibility'] = self.privacy
        if not self.active:
            values['status'] = 'cancelled'
        if self.user_id and self.user_id != self.env.user:
            values['extendedProperties']['shared']['%s_owner_id' % self.env.cr.dbname] = self.user_id.id
        elif not self.user_id:
            # We don't store the real owner identity (mail)
            # We can't store on the shared properties in that case without getting a 403
            # If several odoo users are attendees but the owner is not in odoo, the event will be duplicated on odoo database
            # if we are not the owner, we should change the post values to avoid errors because we don't have enough rights
            # See https://developers.google.com/calendar/concepts/sharing
            keep_keys = ['id', 'attendees', 'start', 'end', 'reminders']
            values = {key: val for key, val in values.items() if key in keep_keys}
            # values['extendedProperties']['private] should be used if the owner is not an odoo user
            values['extendedProperties'] = {
                'private': {
                    '%s_odoo_id' % self.env.cr.dbname: self.id,
                },
            }
        return values

    def _cancel(self):
        # only owner can delete => others refuse the event
        user = self.env.user
        my_cancelled_records = self.filtered(lambda e: e.user_id == user)
        super(Meeting, my_cancelled_records)._cancel()
        attendees = (self - my_cancelled_records).attendee_ids.filtered(lambda a: a.partner_id == user.partner_id)
        attendees.state = 'declined'

    def _notify_attendees(self):
        # filter events before notifying attendees through calendar_alarm_manager
        need_notifs = self.filtered(lambda event: event.alarm_ids and event.stop >= fields.Datetime.now())
        partners = need_notifs.partner_ids
        if partners:
            self.env['calendar.alarm_manager']._notify_next_alarm(partners.ids)
