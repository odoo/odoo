# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4
import requests
import json
import logging

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

class GoogleCalendarService():

    def __init__(self, google_service):
        self.google_service = google_service

    @requires_auth_token
    def get_events(self, sync_token=None, token=None, event_id=None, timeout=TIMEOUT):
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
            day_range = int(ICP.get_param('google_calendar.sync.range_days', default=365))
            _logger.info("Full cal sync, restricting to %s days range", day_range)
            lower_bound = fields.Datetime.subtract(fields.Datetime.now(), days=day_range)
            upper_bound = fields.Datetime.add(fields.Datetime.now(), days=day_range)
            params['timeMin'] = lower_bound.isoformat() + 'Z'  # Z = UTC (RFC3339)
            params['timeMax'] = upper_bound.isoformat() + 'Z'  # Z = UTC (RFC3339)
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
        url = "/calendar/v3/calendars/primary/events/%s?sendUpdates=all" % event_id
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
                raise e
            _logger.info("Google event %s was already deleted" % event_id)


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
            'u': self.google_service.env['ir.config_parameter'].sudo().get_param('database.uuid'),
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
