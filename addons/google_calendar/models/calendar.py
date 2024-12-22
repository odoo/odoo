# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from uuid import uuid4

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService

class Meeting(models.Model):
    _name = 'calendar.event'
    _inherit = ['calendar.event', 'google.calendar.sync']

    MEET_ROUTE = 'meet.google.com'

    google_id = fields.Char(
        'Google Calendar Event Id', compute='_compute_google_id', store=True, readonly=False)
    guests_readonly = fields.Boolean(
        'Guests Event Modification Permission', default=False)
    videocall_source = fields.Selection(selection_add=[('google_meet', 'Google Meet')], ondelete={'google_meet': 'set discuss'})

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

    @api.depends('videocall_location')
    def _compute_videocall_source(self):
        events_with_google_url = self.filtered(lambda event: self.MEET_ROUTE in (event.videocall_location or ''))
        events_with_google_url.videocall_source = 'google_meet'
        super(Meeting, self - events_with_google_url)._compute_videocall_source()

    @api.model
    def _get_google_synced_fields(self):
        return {'name', 'description', 'allday', 'start', 'date_end', 'stop',
                'attendee_ids', 'alarm_ids', 'location', 'privacy', 'active', 'show_as'}

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

    @api.model
    def _check_values_to_sync(self, values):
        """ Return True if values being updated intersects with Google synced values and False otherwise. """
        synced_fields = self._get_google_synced_fields()
        values_to_sync = any(key in synced_fields for key in values)
        return values_to_sync

    @api.model
    def _get_update_future_events_values(self):
        """ Add parameters for updating events within the _update_future_events function scope. """
        update_future_events_values = super()._get_update_future_events_values()
        return {**update_future_events_values, 'need_sync': False}

    @api.model
    def _get_remove_sync_id_values(self):
        """ Add parameters for removing event synchronization while updating the events in super class. """
        remove_sync_id_values = super()._get_remove_sync_id_values()
        return {**remove_sync_id_values, 'google_id': False}

    @api.model
    def _get_archive_values(self):
        """ Return the parameters for archiving events. Do not synchronize events after archiving. """
        archive_values = super()._get_archive_values()
        return {**archive_values, 'need_sync': False}

    def write(self, values):
        recurrence_update_setting = values.get('recurrence_update')
        if recurrence_update_setting in ('all_events', 'future_events') and len(self) == 1:
            values = dict(values, need_sync=False)
        notify_context = self.env.context.get('dont_notify', False)
        if not notify_context and ([self.env.user.id != record.user_id.id for record in self]):
            self._check_modify_event_permission(values)
        res = super(Meeting, self.with_context(dont_notify=notify_context)).write(values)
        if recurrence_update_setting in ('all_events',) and len(self) == 1 and values.keys() & self._get_google_synced_fields():
            self.recurrence_id.need_sync = True
        return res

    def _check_modify_event_permission(self, values):
        # Check if event modification attempt by attendee is valid to avoid duplicate events creation.
        for event in self:
            # Edge case: when restarting the synchronization, guests can write 'need_sync=True' on events.
            google_sync_restart = values.get('need_sync') and len(values)
            if not google_sync_restart and (event.guests_readonly and self.env.user.id != event.user_id.id):
                raise ValidationError(_("The following event can only be updated by the organizer "
                                        "according to the event permissions set on Google Calendar."))

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
            'show_as': 'free' if google_event.is_available() else 'busy',
            'guests_readonly': not bool(google_event.guestsCanModify)
        }
        # Remove 'videocall_location' when not sent by Google, otherwise the local videocall will be discarded.
        if not values.get('videocall_location'):
            values.pop('videocall_location', False)
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
        if related_event['start'] != start:
            values['start'] = start
        if related_event['stop'] != stop:
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
            event = google_event.get_odoo_event(self.env)
            existing_attendees = event.attendee_ids
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

    def action_mass_archive(self, recurrence_update_setting):
        """ Delete recurrence in Odoo if in 'all_events' or in 'future_events' edge case, triggering one mail. """
        self.ensure_one()
        google_service = GoogleCalendarService(self.env['google.service'])
        archive_future_events = recurrence_update_setting == 'future_events' and self == self.recurrence_id.base_event_id
        if recurrence_update_setting == 'all_events' or archive_future_events:
            self.recurrence_id.with_context(is_recurrence=True)._google_delete(google_service, self.recurrence_id.google_id)
            # Increase performance handling 'future_events' edge case as it was an 'all_events' update.
            if archive_future_events:
                recurrence_update_setting = 'all_events'
        super(Meeting, self).action_mass_archive(recurrence_update_setting)

    def _google_values(self):
        if self.allday:
            # For all-day events, 'dateTime' must be set to None to indicate that it's an all-day event.
            # Otherwise, if both 'date' and 'dateTime' are set, Google may not recognize it as an all-day event.
            start = {'date': self.start_date.isoformat(), 'dateTime': None}
            end = {'date': (self.stop_date + relativedelta(days=1)).isoformat(), 'dateTime': None}
        else:
            # For timed events, 'date' must be set to None to indicate that it's not an all-day event.
            # Otherwise, if both 'date' and 'dateTime' are set, Google may not recognize it as a timed event
            start = {'dateTime': pytz.utc.localize(self.start).isoformat(), 'date': None}
            end = {'dateTime': pytz.utc.localize(self.stop).isoformat(), 'date': None}
        reminders = [{
            'method': "email" if alarm.alarm_type == "email" else "popup",
            'minutes': alarm.duration_minutes
        } for alarm in self.alarm_ids]

        attendees = self.attendee_ids
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
            'guestsCanModify': not self.guests_readonly,
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
        if not self.google_id and not self.videocall_location and not self.location:
            values['conferenceData'] = {'createRequest': {'requestId': uuid4().hex}}
        if self.privacy:
            values['visibility'] = self.privacy
        if self.show_as:
            values['transparency'] = 'opaque' if self.show_as == 'busy' else 'transparent'
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
        for event in self:
            # remove the tracking data to avoid calling _track_template in the pre-commit phase
            self.env.cr.precommit.data.pop(f'mail.tracking.create.{event._name}.{event.id}', None)
        super(Meeting, my_cancelled_records)._cancel()
        attendees = (self - my_cancelled_records).attendee_ids.filtered(lambda a: a.partner_id == user.partner_id)
        attendees.state = 'declined'

    def _get_event_user(self):
        self.ensure_one()
        if self.user_id and self.user_id.sudo().google_calendar_token:
            return self.user_id
        return self.env.user
