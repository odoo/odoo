# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import datetime
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from uuid import uuid4

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


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

    @api.model
    def _restart_google_sync(self):
        self.env['calendar.event'].search(self._get_sync_domain()).write({
            'need_sync': True,
        })

    @api.model_create_multi
    def create(self, vals_list):
        notify_context = self.env.context.get('dont_notify', False)
        return super(Meeting, self.with_context(dont_notify=notify_context)).create([
            dict(vals, need_sync=False) if vals.get('recurrence_id') or vals.get('recurrency') else vals
            for vals in vals_list
        ])

    def write(self, values):
        recurrence_update_setting = values.get('recurrence_update')
        if recurrence_update_setting in ('all_events', 'future_events') and len(self) == 1:
            values = dict(values, need_sync=False)
        notify_context = self.env.context.get('dont_notify', False)
        res = super(Meeting, self.with_context(dont_notify=notify_context)).write(values)
        if recurrence_update_setting in ('all_events',) and len(self) == 1 and values.keys() & self._get_google_synced_fields():
            self.recurrence_id.need_sync = True
        return res

    def _get_sync_domain(self):
        # in case of full sync, limit to a range of 1y in past and 1y in the future by default
        ICP = self.env['ir.config_parameter'].sudo()
        day_range = int(ICP.get_param('google_calendar.sync.range_days', default=365))
        lower_bound = fields.Datetime.subtract(fields.Datetime.now(), days=day_range)
        upper_bound = fields.Datetime.add(fields.Datetime.now(), days=day_range)
        return [
            ('partner_ids.user_ids', 'in', self.env.user.id),
            ('stop', '>', lower_bound),
            ('start', '<', upper_bound),
            # Do not sync events that follow the recurrence, they are already synced at recurrence creation
            '!', '&', '&', ('recurrency', '=', True), ('recurrence_id', '!=', False), ('follow_recurrence', '=', True)
        ]

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
        related_event = self.search([('google_id', '=', google_event.id)], limit=1)
        name = google_event.summary or related_event and related_event.name or _("(No title)")
        values = {
            'name': name,
            'description': google_event.description and tools.html_sanitize(google_event.description),
            'location': google_event.location,
            'user_id': google_event.owner(self.env).id,
            'privacy': google_event.visibility or self.default_get(['privacy'])['privacy'],
            'attendee_ids': attendee_commands,
            'alarm_ids': alarm_commands,
            'recurrency': google_event.is_recurrent(),
            'videocall_location': google_event.get_meeting_url(),
            'show_as': 'free' if google_event.is_available() else 'busy'
        }
        if partner_commands:
            # Add partner_commands only if set from Google. The write method on calendar_events will
            # override attendee commands if the partner_ids command is set but empty.
            values['partner_ids'] = partner_commands
        if not google_event.is_recurrence():
            values['google_id'] = google_event.id
        if google_event.is_recurrent() and not google_event.is_recurrence():
            # Propagate the follow_recurrence according to the google result
            values['follow_recurrence'] = google_event.is_recurrence_follower()
        if google_event.start.get('dateTime'):
            # starting from python3.7, use the new [datetime, date].fromisoformat method
            start = parse(google_event.start.get('dateTime')).astimezone(pytz.utc).replace(tzinfo=None)
            stop = parse(google_event.end.get('dateTime')).astimezone(pytz.utc).replace(tzinfo=None)
            values['allday'] = False
        else:
            start = parse(google_event.start.get('date'))
            stop = parse(google_event.end.get('date')) - relativedelta(days=1)
            # Stop date should be exclusive as defined here https://developers.google.com/calendar/v3/reference/events#resource
            # but it seems that's not always the case for old event
            if stop < start:
                stop = parse(google_event.end.get('date'))
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
                'responseStatus': 'accepted',
            }]
        emails = [a.get('email') for a in google_attendees]
        existing_attendees = self.env['calendar.attendee']
        if google_event.exists(self.env):
            existing_attendees = self.browse(google_event.odoo_id(self.env)).attendee_ids
        attendees_by_emails = {tools.email_normalize(a.email): a for a in existing_attendees}
        partners = self._get_sync_partner(emails)
        for attendee in zip(emails, partners, google_attendees):
            email = attendee[0]
            if email in attendees_by_emails:
                # Update existing attendees
                attendee_commands += [(1, attendees_by_emails[email].id, {'state': attendee[2].get('responseStatus')})]
            else:
                # Create new attendees
                if attendee[2].get('self'):
                    partner = self.env.user.partner_id
                elif attendee[1]:
                    partner = attendee[1]
                else:
                    continue
                attendee_commands += [(0, 0, {'state': attendee[2].get('responseStatus'), 'partner_id': partner.id})]
                partner_commands += [(4, partner.id)]
                if attendee[2].get('displayName') and not partner.name:
                    partner.name = attendee[2].get('displayName')
        for odoo_attendee in attendees_by_emails.values():
            # Remove old attendees but only if it does not correspond to the current user.
            email = tools.email_normalize(odoo_attendee.email)
            if email not in emails and email != self.env.user.email:
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

    def _rewrite_recurrence(self, values, time_values, recurrence_values):
        """ Update the events when changing time information within the same day.
        When changing recurrence values, patch the recurrence and recreate events locally.
        The base event is kept in all situations.
        """
        self.ensure_one()
        base_event = self.recurrence_id.base_event_id
        if not base_event:
            raise UserError(_("You can't update a recurrence without base event."))
        [base_time_values] = self.recurrence_id.base_event_id.read(['start', 'stop', 'allday'])
        update_dict = {}
        start_update = fields.Datetime.to_datetime(time_values.get('start'))
        stop_update = fields.Datetime.to_datetime(time_values.get('stop'))
        # Convert the base_event_id hours according to new values: time shift
        if start_update or stop_update:
            if start_update:
                start = base_time_values['start'] + (start_update - self.start)
                stop = base_time_values['stop'] + (start_update - self.start)
                start_date = base_time_values['start'].date() + (start_update.date() - self.start.date())
                stop_date = base_time_values['stop'].date() + (start_update.date() - self.start.date())
                update_dict.update({'start': start, 'start_date': start_date, 'stop': stop, 'stop_date': stop_date})
            if stop_update:
                if not start_update:
                    # Apply the same shift for start
                    start = base_time_values['start'] + (stop_update - self.stop)
                    start_date = base_time_values['start'].date() + (stop_update.date() - self.stop.date())
                    update_dict.update({'start': start, 'start_date': start_date})
                stop = base_time_values['stop'] + (stop_update - self.stop)
                stop_date = base_time_values['stop'].date() + (stop_update.date() - self.stop.date())
                update_dict.update({'stop': stop, 'stop_date': stop_date})

        time_values.update(update_dict)
        if values or time_values or recurrence_values:
            rec_fields = list(super(Meeting, self)._get_recurrent_fields())
            [rec_vals] = base_event.read(rec_fields)

            # Get recurrence information
            old_recurrence = self.env['calendar.recurrence']
            old_recurrence |= self.recurrence_id
            old_recurrence_values = {field: rec_vals.pop(field) for field in rec_fields if field in rec_vals}
            linked_events = self.env['calendar.event']
            linked_events |= old_recurrence.calendar_event_ids

            # Get start date from parameters or base_event and update recurrence
            start_date = time_values['start'].date() if 'start' in time_values else base_event.start.date()
            new_values = {
                **old_recurrence_values,
                **super(Meeting, base_event)._get_recurrence_params_by_date(start_date),
                **recurrence_values,
            }
            new_values.pop('rrule')
            old_recurrence.write(new_values)

            # Optimization: if there are recurrence_values, only base_event won't be archived
            events_to_patch = linked_events if not recurrence_values else base_event

            # Update events info (time, description, etc)
            for record in events_to_patch:
                record.need_sync = False
                # Only time updates within the same day are allowed: combine new time with current day
                if 'start' in time_values:
                    time_values['start'] = datetime.combine(record.start, time_values['start'].time())

                if 'stop' in time_values:
                    time_values['stop'] = datetime.combine(record.stop, time_values['stop'].time())
                record.write({**values, **time_values, **{'need_sync': False}})

            # Update the recurrence structure, reconstruct events except for the base_event
            if recurrence_values:
                old_recurrence.calendar_event_ids = [(4, base_event.id)]
                (linked_events - base_event).write({'need_sync': False, 'active': False})
                old_recurrence._apply_recurrence()

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

        attendees = self.attendee_ids
        if self.user_id and self.user_id != self.env.user and bool(self.user_id.sudo().google_calendar_token):
            # We avoid updating the other attendee status if we are not the organizer
            attendees = self.attendee_ids.filtered(lambda att: att.partner_id == self.env.user.partner_id)
        attendee_values = [{
            'email': attendee.partner_id.email_normalized,
            'responseStatus': attendee.state or 'needsAction',
        } for attendee in attendees if attendee.partner_id.email_normalized]
        # We sort the attendees to avoid undeterministic test fails. It's not mandatory for Google.
        attendee_values.sort(key=lambda k: k['email'])
        values = {
            'id': self.google_id,
            'start': start,
            'end': end,
            'summary': self.name,
            'description': tools.html_sanitize(self.description) if not tools.is_html_empty(self.description) else '',
            'location': self.location or '',
            'guestsCanModify': True,
            'organizer': {'email': self.user_id.email, 'self': self.user_id == self.env.user},
            'attendees': attendee_values,
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
        if not self.google_id and not self.videocall_location:
            values['conferenceData'] = {'createRequest': {'requestId': uuid4().hex}}
        if self.privacy:
            values['visibility'] = self.privacy
        if not self.active:
            values['status'] = 'cancelled'
        if self.user_id and self.user_id != self.env.user and not bool(self.user_id.sudo().google_calendar_token):
            # The organizer is an Odoo user that do not sync his calendar
            values['extendedProperties']['shared']['%s_owner_id' % self.env.cr.dbname] = self.user_id.id
        elif not self.user_id:
            # We can't store on the shared properties in that case without getting a 403. It can happen when
            # the owner is not an Odoo user: We don't store the real owner identity (mail)
            # If we are not the owner, we should change the post values to avoid errors because we don't have
            # write permissions
            # See https://developers.google.com/calendar/concepts/sharing
            keep_keys = ['id', 'summary', 'attendees', 'start', 'end', 'reminders']
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
