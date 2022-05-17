# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import pytz
from werkzeug import urls
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from typing import List

from odoo import fields, models, api, Command, _
from odoo.addons.microsoft_account.models.microsoft_service import MicrosoftService
from odoo.addons.calendar_sync.utils.event import ProviderData
from odoo.addons.calendar_microsoft.utils.event import MicrosoftEvent

PROVIDER_NAME = "microsoft"

def requires_auth_token(func):
    def wrapped(self, *args, **kwargs):
        if not kwargs.get('token'):
            raise AttributeError("An authentication token is required")
        return func(self, *args, **kwargs)
    return wrapped

# --------------------------------------------------------------
# Microsoft Calendar provider
# --------------------------------------------------------------

ATTENDEE_CONVERTER_O2M = {
    'needsAction': 'notresponded',
    'tentative': 'tentativelyaccepted',
    'declined': 'declined',
    'accepted': 'accepted'
}
ATTENDEE_CONVERTER_M2O = {
    'none': 'needsAction',
    'notResponded': 'needsAction',
    'tentativelyAccepted': 'tentative',
    'declined': 'declined',
    'accepted': 'accepted',
    'organizer': 'accepted',
}

class CalendarProvider(models.Model):
    _name = 'calendar.provider'
    _inherit = 'calendar.provider'

    @api.model
    def get_name(self):
        """
        Get the provider name.
        """
        return PROVIDER_NAME

    # ----------------------------------------------------------------------------------
    # AbstractCalendarProvider method overriding
    # ----------------------------------------------------------------------------------

    @api.model
    def get_events_to_sync(self) -> ProviderData:
        """
        Get the list of events to sync from Microsoft provider, packed in a ProviderData structure.
        """
        events = self._get_events()

        # first, try to match recurrences
        # Note that when a recurrence is removed, there is no field in Outlook data to identify
        # the item as a recurrence, so select all deleted items by default.
        recurrence_candidates = filter(lambda e: e.is_recurrence() or e.is_removed(), events)
        mapped_recurrences = self._map_events(recurrence_candidates, are_recurrences=True)

        # then, try to match events
        already_mapped_ids = [r.id for r in mapped_recurrences]
        events_candidates = filter(lambda e: e.id not in already_mapped_ids and not e.is_recurrence(), events)
        mapped_events = self._map_events(events_candidates)

        return self._pack_provider_data(events, mapped_events, mapped_recurrences)

    @api.model
    def _to_odoo_event_values(self, event: MicrosoftEvent) -> dict:
        """
        Convert an event from provider format to Odoo format.
        """
        sensitivity = {
            'normal': 'public',
            'private': 'private',
            'confidential': 'confidential',
        }
        default_privacy = self.env['calendar.event'].default_get(['privacy'])['privacy']

        attendees, partners = self._to_odoo_attendees_and_partners(event)
        start, stop = self._to_odoo_event_time(event)

        values = {
            'name': event.subject or _("(No title)"),
            'description': event.body or event.get('body').get('content'),
            'location': event.location and event.get('location').get('displayName'),
            'user_id': event.odoo_owner(self.env),
            'privacy': sensitivity.get(event.sensitivity, default_privacy),
            'attendee_ids': attendees,
            'partner_ids': partners,
            'allday': event.isAllDay,
            'start': start,
            'stop': stop,
            'show_as': 'free' if event.showAs == 'free' else 'busy',
            'recurrency': event.is_occurrence(),
            'microsoft_id': event.id,
        }

        if event.is_recurrent():
            values['follow_recurrence'] = event.is_occurrence()

        if event.is_occurrence():
            values['microsoft_recurrence_master_id'] = event.seriesMasterId

        alarms = self._to_odoo_alarms(event)
        if alarms:
            values['alarm_ids'] = alarms

        return values

    @api.model
    def _to_odoo_recurrence_values(self, recurrence: MicrosoftEvent) -> dict:
        """
        Convert recurrences from provider format to Odoo format.
        """
        raise Exception("Not overriden")

    # ----------------------------------------------------------------------------------
    # Microsoft specific methods
    # ----------------------------------------------------------------------------------

    @api.model
    def _map_events(self, candidates: List[MicrosoftEvent], are_recurrences=False):
        """
        Map `candidates` events coming from Microsoft calendar to Odoo events.
        Each time a provider event is mapped with an Odoo event, both events are linked using
        the `set_odoo_event` method of MicrosoftEvent.
        @return a list of mapped events
        """
        model = "calendar.recurrence" if are_recurrences else "calendar.event"
        mapped_events = []
        odoo_events = self.env[model].with_context(active_test=False).search([
            '|',
            ('ms_universal_event_id', "in", [e.iCalUId for e in candidates if e.iCalUId]),
            ('ms_organizer_event_id', "in", [e.id for e in candidates if e.id]),
        ])

        # 1. try to match events with Odoo events using their iCalUId
        unmapped_events_with_uids = filter(lambda e: e.iCalUId, candidates)
        odoo_events_with_uids = odoo_events.filtered(lambda e: e.ms_universal_event_id)
        mapping = {e.ms_universal_event_id: e for e in odoo_events_with_uids}

        for ms_event in unmapped_events_with_uids:
            odoo_event = mapping.get(ms_event.iCalUId)
            if odoo_event:
                ms_event.set_odoo_event(odoo_event)
                mapped_events.append(ms_event)

        # 2. try to match unmapped events with Odoo events using their id
        unmapped_events = filter(lambda e: e.id not in mapped_events, candidates)
        mapping = {e.ms_organizer_event_id: e for e in odoo_events}

        for ms_event in unmapped_events:
            odoo_event = mapping.get(ms_event.id)
            if odoo_event:
                # don't forget to also set the global event ID on the Odoo event to ease
                # and improve reliability of future mappings
                odoo_event.ms_universal_event_id = ms_event.iCalUId
                ms_event.set_odoo_event(odoo_event)
                mapped_events.append(ms_event)

        return mapped_events

    @api.model
    def _get_events(self) -> List[MicrosoftEvent]:
        """
        Retrieve all the events that have changed (added/updated/removed) from Microsoft Outlook.
        This is done in 2 steps:
        1) get main changed events (so single events and serie masters)
        2) get occurrences linked to a serie masters (to retrieve all needed details such as iCalUId)
        """
        user = self.env.user
        user_token = user._get_microsoft_calendar_token()
        sync_token = user.microsoft_calendar_sync_token

        events, next_sync_token = self._get_events_delta(sync_token=sync_token, token=user_token)

        # get occurences details for all serie masters
        for master in filter(lambda e: e.get('type') == 'seriesMaster', events):
            res = self._get_occurrence_details(master['id'], token=user_token)
            events.extend(res)

        # update the sync token for the next sync
        user.microsoft_calendar_sync_token = next_sync_token

        return [MicrosoftEvent(e) for e in events]

    @api.model
    def _to_odoo_attendees_and_partners(self, event: MicrosoftEvent) -> tuple:
        """
        Get attendees and partners in Odoo format (commands), from a Microsoft event.
        """
        attendee_commands = []
        partner_commands = []

        attendees = event.attendees or []
        emails = [a.get('emailAddress').get('address') for a in attendees]
        partners = self.env['mail.thread']._mail_find_partner_from_emails(emails, records=self, force_create=True)

        existing_attendees = self.env['calendar.attendee']
        if event.has_odoo_event():
            existing_attendees = self.env['calendar.attendee'].search([
                ('event_id', '=', event.get_odoo_event()),
                ('email', 'in', emails)])
        elif self.env.user.partner_id.email not in emails:
            attendee_commands += [Command.create({'state': 'accepted', 'partner_id': self.env.user.partner_id.id})]
            partner_commands += [Command.link(self.env.user.partner_id.id)]

        attendees_by_emails = {a.email: a for a in existing_attendees}

        for email, partner, attendee in zip(emails, partners, attendees):
            state = ATTENDEE_CONVERTER_M2O.get(attendee.get('status').get('response'))

            if email in attendees_by_emails:
                # Update existing attendees
                attendee_commands += [Command.update(attendees_by_emails[email].id, {'state': state})]
            elif partner:
                # Create new attendees
                attendee_commands += [Command.create({'state': state, 'partner_id': partner.id})]
                partner_commands += [Command.link(partner.id)]
                if attendee.get('emailAddress').get('name') and not partner.name:
                    partner.name = attendee.get('emailAddress').get('name')
        for odoo_attendee in attendees_by_emails.values():
            # Remove old attendees
            if odoo_attendee.email not in emails:
                attendee_commands += [Command.delete(odoo_attendee.id)]
                partner_commands += [Command.unlink(odoo_attendee.partner_id.id)]

        return attendee_commands, partner_commands

    @api.model
    def _to_odoo_event_time(self, event: MicrosoftEvent) -> tuple:
        """
        Get the start and stop time in Odoo format, from a Microsoft event.
        """
        start_timezone = pytz.timezone(event.start.get('timeZone'))
        stop_timezone = pytz.timezone(event.end.get('timeZone'))

        start = parse(event.start.get('dateTime')).astimezone(start_timezone).replace(tzinfo=None)
        stop = parse(event.end.get('dateTime')).astimezone(stop_timezone).replace(tzinfo=None)
        if event.isAllDay:
            stop -= relativedelta(days=1)

        return start, stop

    @api.model
    def _to_odoo_alarms(self, event: MicrosoftEvent):
        pass

    # -------------------------------------------------------------------
    # API END-POINTS MANAGEMENT
    # -------------------------------------------------------------------

    @api.model
    def _get_service(self):
        return self.env['microsoft.service']

    @requires_auth_token
    def _get_events_from_paginated_url(self, url, token=None, params=None):
        """
        Get a list of events from a paginated URL.
        Each page contains a link to the next page, so loop over all the pages to get all the events.
        """
        service = self._get_service()
        headers = {
            'Content-type': 'application/json',
            'Authorization': 'Bearer %s' % token,
            'Prefer': 'outlook.body-content-type="text", odata.maxpagesize=50'
        }
        if not params:
            params = {
                'startDateTime': fields.Datetime.subtract(fields.Datetime.now(), years=3).strftime("%Y-%m-%dT00:00:00Z"),
                'endDateTime': fields.Datetime.add(fields.Datetime.now(), years=3).strftime("%Y-%m-%dT00:00:00Z"),
            }

        # get the first page of events
        _, data, _ = service._do_request(url, params, headers, method='GET')

        # and then, loop on other pages to get all the events
        events = data.get('value', [])
        next_page_token = data.get('@odata.nextLink')
        while next_page_token:
            _, data, _ = service._do_request(next_page_token, {}, headers, preuri='', method='GET')
            next_page_token = data.get('@odata.nextLink')
            events += data.get('value', [])

        token_url = data.get('@odata.deltaLink')
        next_sync_token = urls.url_parse(token_url).decode_query().get('$deltatoken', False) if token_url else None

        return events, next_sync_token

    @requires_auth_token
    def _get_events_delta(self, sync_token=None, token=None):
        """
        Get a set of events that have been added, deleted or updated in a time range.
        See: https://docs.microsoft.com/en-us/graph/api/event-delta?view=graph-rest-1.0&tabs=http
        """
        url = "/v1.0/me/calendarView/delta"
        params = {'$deltatoken': sync_token} if sync_token else None

        try:
            events, next_sync_token = self._get_events_from_paginated_url(url, params=params, token=token)
        except requests.HTTPError as e:
            if e.response.status_code == 410 and 'fullSyncRequired' in str(e.response.content) and sync_token:
                # retry with a full sync
                return self._get_events_delta(token=token)
            raise e

        # event occurrences (from a recurrence) are retrieved separately to get all their info,
        # # and mainly the iCalUId attribute which is not provided by the 'get_delta' api end point
        events = list(filter(lambda e: e.get('type') != 'occurrence', events))

        return events, next_sync_token

    @requires_auth_token
    def _get_occurrence_details(self, serieMasterId, token=None):
        """
        Get all occurrences details from a serie master.
        See: https://docs.microsoft.com/en-us/graph/api/event-list-instances?view=graph-rest-1.0&tabs=http
        """
        url = f"/v1.0/me/events/{serieMasterId}/instances"

        events, _ = self._get_events_from_paginated_url(url, token=token)
        return events
