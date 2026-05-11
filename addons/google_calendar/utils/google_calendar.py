# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4
import requests
import json
import logging
from contextlib import suppress

from odoo import fields
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


class GoogleCalendarRateLimit(Exception):
    """Raised when Google Calendar API answers with a rate-limit / quota response.
    Callers performing bulk operations (e.g. account reset) should catch this
    and apply truncated exponential backoff per
    https://developers.google.com/workspace/calendar/api/guides/quota
    """


# https://developers.google.com/workspace/calendar/api/guides/errors
_RATE_LIMIT_REASONS = frozenset({'rateLimitExceeded', 'userRateLimitExceeded', 'quotaExceeded'})
_ALREADY_GONE_REASONS = frozenset({'eventCancelled'})


def _google_error_reason(http_error):
    with suppress(ValueError, KeyError, IndexError, TypeError):
        return http_error.response.json()['error']['errors'][0].get('reason')

    return None


class GoogleCalendarService():

    def __init__(self, google_service):
        self.google_service = google_service

    @requires_auth_token
    def get_events(self, sync_token=None, token=None, event_id=None, search_params=None, timeout=TIMEOUT):
        url = "/calendar/v3/calendars/primary/events"
        if event_id:
            url += f"/{event_id}"
        headers = {'Content-type': 'application/json'}
        params = {'access_token': token}
        if sync_token:
            params['syncToken'] = sync_token
        else:
            # full sync, limit to a range of 1y in past to 1y in the futur by default
            ICP = self.google_service.env['ir.config_parameter'].sudo()
            day_range = ICP.get_int('google_calendar.sync.range_days') or 365
            _logger.info("Full cal sync, restricting to %s days range", day_range)
            lower_bound = fields.Datetime.subtract(fields.Datetime.now(), days=day_range)
            upper_bound = fields.Datetime.add(fields.Datetime.now(), days=day_range)
            params['timeMin'] = lower_bound.isoformat() + 'Z'  # Z = UTC (RFC3339)
            params['timeMax'] = upper_bound.isoformat() + 'Z'  # Z = UTC (RFC3339)
        if search_params:
            params.update(search_params)
        try:
            status, data, time = self.google_service._do_request(url, params, headers, method='GET', timeout=timeout)
        except requests.HTTPError as e:
            if e.response.status_code == 410 and 'fullSyncRequired' in str(e.response.content):
                raise InvalidSyncToken("Invalid sync token. Full sync required")
            raise e

        if event_id:
            next_sync_token = None
            default_reminders = ()
            return GoogleEvent([data]), next_sync_token, default_reminders

        events = data.get('items', [])
        next_page_token = data.get('nextPageToken')
        while next_page_token:
            params = {'access_token': token, 'pageToken': next_page_token}
            status, data, time = self.google_service._do_request(url, params, headers, method='GET', timeout=timeout)
            next_page_token = data.get('nextPageToken')
            events += data.get('items', [])

        next_sync_token = data.get('nextSyncToken')
        default_reminders = data.get('defaultReminders')

        return GoogleEvent(events), next_sync_token, default_reminders

    @requires_auth_token
    def insert(self, values, token=None, timeout=TIMEOUT, need_video_call=True):
        send_updates = self.google_service.env.context.get('send_updates', True)
        url = "/calendar/v3/calendars/primary/events?conferenceDataVersion=%d&sendUpdates=%s" % (1 if need_video_call else 0, "all" if send_updates else "none")
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        if not values.get('id'):
            values['id'] = uuid4().hex
        _dummy, google_values, _dummy = self.google_service._do_request(url, json.dumps(values), headers, method='POST', timeout=timeout)
        return google_values

    @requires_auth_token
    def patch(self, event_id, values, token=None, timeout=TIMEOUT):
        send_updates = self.google_service.env.context.get('send_updates', True)
        url = "/calendar/v3/calendars/primary/events/%s?sendUpdates=%s&conferenceDataVersion=1" % (event_id, "all" if send_updates else "none")
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        self.google_service._do_request(url, json.dumps(values), headers, method='PATCH', timeout=timeout)

    @requires_auth_token
    def delete(self, event_id, token=None, timeout=TIMEOUT):
        # Deleting a recurring-event master cancels every instance (and any
        # detached "exception" instances) on Google's side in a single call.
        url = "/calendar/v3/calendars/primary/events/%s?sendUpdates=all" % event_id
        headers = {'Content-type': 'application/json'}
        params = {'access_token': token}
        try:
            self.google_service._do_request(url, params, headers=headers, method='DELETE', timeout=timeout)
        except requests.HTTPError as e:
            code = e.response.status_code
            reason = _google_error_reason(e)

            # Already gone (deleted on Google's side or cancelled): treat as success.
            if code in (404, 410) or reason in _ALREADY_GONE_REASONS:
                _logger.info("Google event %s already deleted (HTTP %s, reason=%s)", event_id, code, reason)
                return

            # Rate-limit / quota: surface a typed exception so bulk callers can back off.
            if code == 429 or reason in _RATE_LIMIT_REASONS:
                raise GoogleCalendarRateLimit(reason or "HTTP %s" % code) from e

            raise


    #################################
    ##  MANAGE CONNEXION TO GMAIL  ##
    #################################


    def is_authorized(self, user):
        return bool(user.sudo().google_calendar_rtoken)

    def _get_calendar_scope(self, RO=False):
        readonly = '.readonly' if RO else ''
        return 'https://www.googleapis.com/auth/calendar%s' % (readonly)

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
