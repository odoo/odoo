# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import pytz
from dateutil.parser import parse

from odoo import api, models, Command
from odoo.tools import email_normalize

from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService


class RecurrenceRule(models.Model):
    _name = 'calendar.recurrence'
    _inherit = ['calendar.recurrence', 'google.calendar.sync']

    def _apply_recurrence(self, specific_values_creation=None, no_send_edit=False, generic_values_creation=None):
        events = self.filtered('need_sync').calendar_event_ids
        detached_events = super()._apply_recurrence(specific_values_creation, no_send_edit,
                                                    generic_values_creation)

        google_service = GoogleCalendarService(self.env['google.service'])

        # If a synced event becomes a recurrence, the event needs to be deleted from
        # Google since it's now the recurrence which is synced.
        # Those events are kept in the database and their google_id is updated
        # according to the recurrence google_id, therefore we need to keep an inactive copy
        # of those events with the original google id. The next sync will then correctly
        # delete those events from Google.
        vals = []
        for event in events.filtered('google_id'):
            if event.active and event.google_id != event.recurrence_id._get_event_google_id(event):
                vals += [{
                    'name': event.name,
                    'google_id': event.google_id,
                    'start': event.start,
                    'stop': event.stop,
                    'active': False,
                    'need_sync': True,
                }]
                event._google_delete(google_service, event.google_id)
                event.google_id = False
        self.env['calendar.event'].create(vals)

        self.calendar_event_ids.need_sync = False
        return detached_events

    def _get_event_google_id(self, event):
        """Return the Google id of recurring event.
        Google ids of recurrence instances are formatted as: {recurrence google_id}_{UTC starting time in compacted ISO8601}
        """
        if self.google_id:
            if event.allday:
                time_id = event.start_date.isoformat().replace('-', '')
            else:
                # '-' and ':' are optional in ISO8601
                start_compacted_iso8601 = event.start.isoformat().replace('-', '').replace(':', '')
                # Z at the end for UTC
                time_id = '%sZ' % start_compacted_iso8601
            return '%s_%s' % (self.google_id, time_id)
        return False

    def _write_events(self, values, dtstart=None):
        values.pop('google_id', False)
        # If only some events are updated, sync those events.
        values['need_sync'] = bool(dtstart)
        return super()._write_events(values, dtstart=dtstart)

    def _cancel(self):
        self.calendar_event_ids._cancel()
        super()._cancel()

    def _get_google_synced_fields(self):
        return {'rrule'}

    @api.model
    def _restart_google_sync(self):
        self.env['calendar.recurrence'].search(self._get_sync_domain()).write({
            'need_sync': True,
        })

    def _update_attendees_status(self, gevent):
        existing_attendees = self.calendar_event_ids.attendee_ids
        existing_attendees_emails = [email_normalize(e) for e in set(existing_attendees.mapped('email'))]
        google_attendees = gevent.attendees or []
        google_attendees_emails = [a.get('email') for a in google_attendees]

        if google_attendees:
            partners = self.env['mail.thread']._mail_find_partner_from_emails(
                google_attendees_emails, records=self, force_create=True
            )

            # update existing attendees, create new ones
            for email, partner, google_attendee in zip(google_attendees_emails, partners, gevent.attendees):
                if email in existing_attendees_emails:
                    existing_attendees.filtered(lambda a: a.email == email).write(
                        {'state': google_attendee.get('responseStatus')}
                    )
                else:
                    if google_attendee.get('self'):
                        partner = self.env.user.partner_id

                    self.calendar_event_ids.write({
                        'attendee_ids': [
                            Command.create({'state': google_attendee.get('responseStatus'), 'partner_id': partner.id})
                        ]
                    })

                    if google_attendee.get('displayName') and not partner.name:
                        partner.name = google_attendee.get('displayName')

        # Remove old attendees except the organizer. Sometimes, several partners have the same email.
        if gevent.organizer and gevent.organizer.get('email'):
            google_attendees_emails += [gevent.organizer.get('email')]

        for odoo_attendee_email in existing_attendees_emails:
            if odoo_attendee_email not in google_attendees_emails:
                attendees = existing_attendees.exists().filtered(lambda a: a.email == odoo_attendee_email)
                self.calendar_event_ids.write({
                    'need_sync': False,
                    'partner_ids': [Command.unlink(a.partner_id.id) for a in attendees]
                })

    def _write_from_google(self, gevent, vals):
        """
        Update a Odoo event recurrence from a Google event recurrence.
        @note: gevent contains one google event recurrence only.
        """
        def _have_base_event_time_fields_changed(new_values):
            fields = ['start', 'stop', 'allday']
            old_values = self.base_event_id and self.base_event_id.read(fields)[0]
            return old_values and any(new_values[key] != old_values[key] for key in fields)

        self.ensure_one()
        current_rrule = self.rrule

        # In Odoo, the timezone is stored on the recurrence and not on the event,
        # so use the timezone from google event to update the current recurrence.
        super()._write_from_google(gevent, dict(vals, event_tz=gevent.start.get('timeZone')))

        new_event_values = self.env["calendar.event"]._odoo_values(gevent)

        # when time fields have been modified, recurrence has to be recreated from the base event
        # with its new field values
        if _have_base_event_time_fields_changed(new_event_values):
            events_to_remove = self.calendar_event_ids - self.base_event_id
            events_to_remove.google_id = False
            events_to_remove.unlink()

            self.base_event_id.with_context(dont_notify=True).write(
                dict(new_event_values, google_id=False, need_sync=False)
            )

            # if the recurrence rule has not been modified, we just have
            # to apply the recurrence rule to update existing events.
            # no event will be excluded/detached from the recurrence.
            if self.rrule == current_rrule:
                self.with_context(dont_notify=True)._apply_recurrence()
        else:
            time_fields = (
                self.env["calendar.event"]._get_time_fields() | self.env["calendar.event"]._get_recurrent_fields()
            )
            # We avoid to write time_fields because they are not shared between events.
            self._write_events(dict(
                {
                    field: value
                    for field, value in new_event_values.items()
                    if field not in time_fields
                },
                need_sync=False,
            ))

        # If the recurrence rule has changed, applying the new rule may create some orphan events
        # which may be reused for another new recurrence so we keep them.
        # Note: rule update checking has to be done after having updated time fields (if required), because
        # the event google_id field is computed based on these time fields, and more specifically the start datetime.
        orphan_events = None
        if self.rrule != current_rrule:
            orphan_events = self._apply_recurrence()
            orphan_events.google_id = False

        # Once the recurrence structure is updated, let's update the status of attendees
        self._update_attendees_status(gevent)

        return orphan_events

    def _find_events_from_orphans(self, expected_ranges, orphan_records):
        """
        Search if some events from the list of orphan events, matching the expected ranges
        of events of the new recurrence.
        """
        return orphan_records.filtered(lambda e: e._range() in expected_ranges) if orphan_records else None

    def _create_from_google(self, gevents, vals_list, orphan_records=None):
        attendee_values = {}
        for gevent, vals in zip(gevents, vals_list):
            base_values = dict(
                self.env['calendar.event']._odoo_values(gevent),  # FIXME default reminders
                need_sync=False,
            )
            # If we convert a single event into a recurrency on Google, we should reuse this event on Odoo
            # Google reuse the event google_id to identify the recurrence in that case
            base_event = self.env['calendar.event'].search([('google_id', '=', vals['google_id'])])
            if not base_event:
                # if this new recurrence comes from a recurrence split, we should try to reuse orphan events
                # to find the new recurrence base event id
                start, stop, _ = self._odoo_dates_from_google_dates(gevent)
                base_event = self._find_events_from_orphans([(start, stop)], orphan_records)

            if not base_event:
                base_event = self.env['calendar.event'].create(base_values)
            else:
                # We override the base_event values because they could have been changed in Google interface
                # The event google_id will be recalculated once the recurrence is created
                base_event.write(dict(base_values, google_id=False))

            vals['base_event_id'] = base_event.id
            vals['calendar_event_ids'] = [(4, base_event.id)]
            # event_tz is written on event in Google but on recurrence in Odoo
            vals['event_tz'] = gevent.start.get('timeZone')
            attendee_values[base_event.id] = {'attendee_ids': base_values.get('attendee_ids')}

        recurrences = super(RecurrenceRule, self.with_context(dont_notify=True))._create_from_google(gevents, vals_list)
        generic_values_creation = {
            rec.id: attendee_values[rec.base_event_id.id]
            for rec in recurrences if attendee_values.get(rec.base_event_id.id)
        }

        # if some orphan events exist, try to reuse them by matching expected event ranges from the new recurrence
        # with these orphan events
        if orphan_records:
            time_fields = (
                self.env["calendar.event"]._get_time_fields() | self.env["calendar.event"]._get_recurrent_fields()
            )
            for r in recurrences:
                gevent = [e for e in gevents if e.id == r.google_id][0]
                new_values = self.env["calendar.event"]._odoo_values(gevent)
                expected_ranges = r._range_calculation(r.base_event_id, r.base_event_id.stop - r.base_event_id.start)
                r.calendar_event_ids |= r._find_events_from_orphans(expected_ranges, orphan_records)

                # but do not forget to update these orphan events according to their new recurrence
                r._write_events(dict(
                    {
                        field: value
                        for field, value in new_values.items()
                        if field not in time_fields
                    },
                    need_sync=False,
                ))
                r._update_attendees_status(gevent)

        recurrences.with_context(dont_notify=True)._apply_recurrence(generic_values_creation=generic_values_creation)

        return recurrences

    def _get_sync_domain(self):
        # Empty rrule may exists in historical data. It is not a desired behavior but it could have been created with
        # older versions of the module. When synced, these recurrency may come back from Google after database cleaning
        # and trigger errors as the records are not properly populated.
        # We also prevent sync of other user recurrent events.
        return [('calendar_event_ids.user_id', '=', self.env.user.id), ('rrule', '!=', False)]

    @api.model
    def _odoo_values(self, google_recurrence, default_reminders=()):
        return {
            'rrule': google_recurrence.rrule,
            'google_id': google_recurrence.id,
        }

    def _google_values(self):
        event = self._get_first_event()
        if not event:
            return {}
        values = event._google_values()
        values['id'] = self.google_id
        if not self._is_allday():
            values['start']['timeZone'] = self.event_tz or 'Etc/UTC'
            values['end']['timeZone'] = self.event_tz or 'Etc/UTC'

        # DTSTART is not allowed by Google Calendar API.
        # Event start and end times are specified in the start and end fields.
        rrule = re.sub('DTSTART:[0-9]{8}T[0-9]{1,8}\\n', '', self.rrule)
        # UNTIL must be in UTC (appending Z)
        # We want to only add a 'Z' to non UTC UNTIL values and avoid adding a second.
        # 'RRULE:FREQ=DAILY;UNTIL=20210224T235959;INTERVAL=3 --> match UNTIL=20210224T235959
        # 'RRULE:FREQ=DAILY;UNTIL=20210224T235959 --> match
        rrule = re.sub(r"(UNTIL=\d{8}T\d{6})($|;)", r"\1Z\2", rrule)
        values['recurrence'] = ['RRULE:%s' % rrule] if 'RRULE:' not in rrule else [rrule]
        property_location = 'shared' if event.user_id else 'private'
        values['extendedProperties'] = {
            property_location: {
                '%s_odoo_id' % self.env.cr.dbname: self.id,
            },
        }
        return values
