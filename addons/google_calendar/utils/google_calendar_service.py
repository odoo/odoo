# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4
import requests
import json
import logging

from odoo import fields, Command
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendar
from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.addons.google_account.models.google_service import TIMEOUT


_logger = logging.getLogger(__name__)


def requires_auth_token(func):
    def wrapped(self, *args, **kwargs):
        if not kwargs.get('token'):
            raise AttributeError("An authentication token is required")
        return func(self, *args, **kwargs)
    return wrapped


class InvalidSyncToken(Exception):
    pass


class CalendarNotFound(Exception):
    pass


class GoogleCalendarService:

    def __init__(self, google_service):
        self.google_service = google_service

    @requires_auth_token
    def get_calendars(self, sync_token=None, token=None, timeout=TIMEOUT):
        url = "/calendar/v3/users/me/calendarList"
        headers = {'Content-type': 'application/json'}
        params = {'access_token': token}
        if sync_token:
            params['syncToken'] = sync_token

        items, data = self._fetch_paginated_items(url, params, headers, timeout)
        return GoogleCalendar(items), data

    def _get_or_create_calendar(self, calendar_data):
        calendar_id, primary = calendar_data.get('id'), calendar_data.get('primary')

        if primary:
            primary_calendar = self.google_service.env.user.primary_calendar
            if primary_calendar:
                return primary_calendar
        else:
            calendar = self.google_service.env.user.calendar_ids.filtered(lambda c: c.google_id == calendar_id)
            if calendar:
                return calendar

        return self.google_service.env['calendar.calendar'].create({
            'google_id': calendar_id,
            'name': calendar_data.get('summary'),
            'calendar_users': [Command.create({
                'user_id': self.google_service.env.user.id,
                'access_role': calendar_data.get('accessRole') or 'freeBusyReader',
                'is_filter_active': True,
                'is_filter_checked': True,
            })],
        })

    @requires_auth_token
    def insert_calendar(self, values, token, timeout=TIMEOUT):
        url = "/calendar/v3/calendars"
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        _logger.info("insert_calendar - values: %s", json.dumps(values))
        _, google_values, _ = self.google_service._do_request(url, json.dumps(values), headers=headers, method='POST', timeout=timeout)
        return google_values

    @requires_auth_token
    def patch_calendar(self, calendar, values, token, timeout=TIMEOUT):
        url = "/calendar/v3/calendars/%s" % calendar
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        _logger.info("patch_calendar - values: %s", json.dumps(values))
        self.google_service._do_request(url, json.dumps(values), headers=headers, method='PATCH', timeout=timeout)

    @requires_auth_token
    def delete_calendar(self, calendar, token, timeout=TIMEOUT):
        url = "/calendar/v3/calendars/%s" % calendar
        headers = {'Content-type': 'application/json'}
        params = {'access_token': token}
        _logger.info("delete_calendar - calendar: %s", calendar.id)
        self.google_service._do_request(url, params=params, headers=headers, method='DELETE', timeout=timeout)

    @requires_auth_token
    def get_events(self, sync_token=None, token=None, event_id=None, calendar=None, search_params=None, timeout=TIMEOUT):
        url = f"/calendar/v3/calendars/{calendar.get_google_path() if calendar else 'primary'}/events"
        headers = {'Content-type': 'application/json'}
        params = {'access_token': token}
        if search_params:
            params.update(search_params)

        if event_id:
            url += f"/{event_id}"
            _, data, _ = self._do_request_with_error_handling(url, params, headers, timeout)
            return GoogleEvent([data]), None, ()

        if sync_token:
            params['syncToken'] = sync_token
        else:
            # full sync, limit to a range of 1y in past to 1y in the future by default
            ICP = self.google_service.env['ir.config_parameter'].sudo()
            day_range = ICP.get_int('google_calendar.sync.range_days') or 365
            _logger.info("Full cal sync, restricting to %s days range", day_range)
            lower_bound = fields.Datetime.subtract(fields.Datetime.now(), days=day_range)
            upper_bound = fields.Datetime.add(fields.Datetime.now(), days=day_range)
            params['timeMin'] = lower_bound.isoformat() + 'Z'  # Z = UTC (RFC3339)
            params['timeMax'] = upper_bound.isoformat() + 'Z'  # Z = UTC (RFC3339)

        try:
            events, data = self._fetch_paginated_items(url, params, headers, timeout)
        except CalendarNotFound:
            # This usually means one of two things:
            # - the calendar was both deleted in Google Calendar and edited in Odoo before the last sync
            # - the user connected a different Google account in Odoo
            # It should be recreated in the Odoo->Google part of the sync.
            calendar.write({'need_sync': True})
            return GoogleEvent([]), None, ()

        return GoogleEvent(events), data.get('nextSyncToken'), data.get('defaultReminders')

    def _do_request_with_error_handling(self, url, params, headers, timeout):
        try:
            status, data, time = self.google_service._do_request(url, params, headers, method='GET', timeout=timeout)
        except requests.HTTPError as e:
            if e.response.status_code == 410 and 'fullSyncRequired' in str(e.response.content):
                raise InvalidSyncToken("Invalid sync token. Full sync required")
            raise
        return status, data, time

    def _fetch_paginated_items(self, url, params, headers, timeout):
        status, data, _ = self._do_request_with_error_handling(url, params, headers, timeout)
        if status == 404:
            raise CalendarNotFound("Cannot fetch calendar events, calendar does not exist on Google Calendar yet. %s", url)

        items = data.get('items', [])
        next_page_token = data.get('nextPageToken')
        while next_page_token:
            page_params = {**params, 'pageToken': next_page_token}
            _, data, _ = self.google_service._do_request(url, page_params, headers, method='GET', timeout=timeout)
            next_page_token = data.get('nextPageToken')
            items += data.get('items', [])

        return items, data

    @requires_auth_token
    def insert(self, values, calendar, token=None, timeout=TIMEOUT, need_video_call=True):
        send_updates = self.google_service.env.context.get('send_updates', True)
        url = ("/calendar/v3/calendars/%s/events?conferenceDataVersion=%d&sendUpdates=%s" %
               (calendar, 1 if need_video_call else 0, "all" if send_updates else "none"))
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        if not values.get('id'):
            values['id'] = uuid4().hex
        _dummy, google_values, _dummy = self.google_service._do_request(url, json.dumps(values), headers, method='POST', timeout=timeout)
        return google_values

    @requires_auth_token
    def patch(self, event_id, values, calendar, token=None, timeout=TIMEOUT):
        # Could be optimized for quota usage. From google docs:
        # 'Note that each patch request consumes three quota units; prefer using a get followed by an update.'
        # https://developers.google.com/workspace/calendar/api/v3/reference/events/patch
        send_updates = self.google_service.env.context.get('send_updates', True)
        url = ("/calendar/v3/calendars/%s/events/%s?sendUpdates=%s&conferenceDataVersion=1" %
               (calendar, event_id, "all" if send_updates else "none"))
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        self.google_service._do_request(url, json.dumps(values), headers, method='PATCH', timeout=timeout)

    @requires_auth_token
    def move(self, event_id, source, destination, send_updates, token=None, timeout=TIMEOUT):
        url = ("/calendar/v3/calendars/%s/events/%s/move?sendUpdates=%s&destination=%s" %
               (source, event_id, "all" if send_updates else "none", destination))
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        return self.google_service._do_request(url, headers=headers, method='POST', timeout=timeout)

    @requires_auth_token
    def delete(self, event_id, calendar, token=None, timeout=TIMEOUT):
        url = "/calendar/v3/calendars/%s/events/%s?sendUpdates=all" % (calendar, event_id)
        headers = {'Content-type': 'application/json'}
        params = {'access_token': token}
        # Delete all events from recurrence in a single request to Google and triggering a single mail.
        # The 'singleEvents' parameter is a trick that tells Google API to delete all recurrent events individually,
        # making the deletion be handled entirely on their side, and then we archive the events in Odoo.
        is_recurrence = self.google_service.env.context.get('is_recurrence', True)
        if is_recurrence:
            params['singleEvents'] = 'true'
        try:
            self.google_service._do_request(url, params, headers=headers, method='DELETE', timeout=timeout)
        except requests.HTTPError as e:
            # For some unknown reason Google can also return a 403 response when the event is already cancelled.
            if e.response.status_code not in (410, 403):
                raise
            _logger.info("Google event %s was already deleted", event_id)

    #################################
    ##  MANAGE CONNEXION TO GMAIL  ##
    #################################

    def is_authorized(self, user):
        return bool(user.sudo().google_calendar_rtoken)

    def _get_calendar_scope(self, RO=False):
        readonly = '.readonly' if RO else ''
        return 'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/calendar%s' % (readonly)

    def _google_authentication_url(self, from_url='http://www.odoo.com'):
        state = {
            'd': self.google_service.env.cr.dbname,
            's': 'calendar',
            'f': from_url,
            'u': self.google_service.env['ir.config_parameter'].sudo().get_str('database.uuid'),
        }
        base_url = self.google_service.env.context.get('base_url') or self.google_service.get_base_url()
        return self.google_service._get_authorize_uri(
            'calendar',
            self._get_calendar_scope(),
            base_url + '/google_account/authentication',
            state=json.dumps(state),
            approval_prompt='force',
            access_type='offline'
        )

    def _can_authorize_google(self, user):
        return user.has_group('base.group_erp_manager')
