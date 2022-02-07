# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import json
import logging

from werkzeug import urls

from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_account.models.microsoft_service import TIMEOUT


_logger = logging.getLogger(__name__)

def requires_auth_token(func):
    def wrapped(self, *args, **kwargs):
        if not kwargs.get('token'):
            raise AttributeError("An authentication token is required")
        return func(self, *args, **kwargs)
    return wrapped

class InvalidSyncToken(Exception):
    pass

class MicrosoftCalendarService():

    def __init__(self, microsoft_service):
        self.microsoft_service = microsoft_service

    @requires_auth_token
    def get_events(self, sync_token=None, token=None, timeout=TIMEOUT):
        url = "/v1.0/me/calendarView/delta"
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token, 'Prefer': 'outlook.body-content-type="html"'}
        params = {}
        if sync_token:
            params['$deltatoken'] = sync_token
        else:
            params['startDateTime'] = '2016-12-01T00:00:00Z'
            params['endDateTime'] = '2030-1-01T00:00:00Z'
        try:
            status, data, time = self.microsoft_service._do_request(url, params, headers, method='GET', timeout=timeout)
        except requests.HTTPError as e:
            if e.response.status_code == 410 and 'fullSyncRequired' in str(e.response.content):
                raise InvalidSyncToken("Invalid sync token. Full sync required")
            raise e

        events = data.get('value', [])
        next_page_token = data.get('@odata.nextLink')
        while next_page_token:
            status, data, time = self.microsoft_service._do_request(next_page_token, {}, headers, preuri='', method='GET', timeout=timeout)
            next_page_token = data.get('@odata.nextLink')
            events += data.get('value', [])

        next_sync_token_url = data.get('@odata.deltaLink')
        next_sync_token = urls.url_parse(next_sync_token_url).decode_query().get('$deltatoken', False)

        default_reminders = data.get('defaultReminders')

        return MicrosoftEvent(events), next_sync_token, default_reminders

    @requires_auth_token
    def insert(self, values, token=None, timeout=TIMEOUT):
        url = "/v1.0/me/calendar/events"
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        if not values.get('id'):
            values.pop('id', None)
        dummy, data, dummy = self.microsoft_service._do_request(url, json.dumps(values, separators=(',', ':')), headers, method='POST', timeout=timeout)
        return data['id']

    @requires_auth_token
    def patch(self, event_id, values, token=None, timeout=TIMEOUT):
        url = "/v1.0/me/calendar/events/%s" % event_id
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        self.microsoft_service._do_request(url, json.dumps(values, separators=(',', ':')), headers, method='PATCH', timeout=timeout)

    @requires_auth_token
    def delete(self, event_id, token=None, timeout=TIMEOUT):
        url = "/v1.0/me/calendar/events/%s" % event_id
        headers = {'Authorization': 'Bearer %s' % token}
        params = {}
        try:
            self.microsoft_service._do_request(url, params, headers=headers, method='DELETE', timeout=timeout)
        except requests.HTTPError as e:
            # For some unknown reason Microsoft can also return a 403 response when the event is already cancelled.
            if e.response.status_code not in (410, 403):
                raise e
            _logger.info("Microsoft event %s was already deleted" % event_id)

    @requires_auth_token
    def answer(self, event_id, answer, values, token=None, timeout=TIMEOUT):
        url = "/v1.0/me/calendar/events/%s/%s" % (event_id, answer)
        headers = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % token}
        self.microsoft_service._do_request(url, json.dumps(values), headers, method='POST', timeout=timeout)


    #####################################
    ##  MANAGE CONNEXION TO MICROSOFT  ##
    #####################################

    def is_authorized(self, user):
        return bool(user.sudo().microsoft_calendar_rtoken)

    def _get_calendar_scope(self):
        return 'offline_access openid Calendars.ReadWrite'

    def _microsoft_authentication_url(self, from_url='http://www.odoo.com'):
        return self.microsoft_service._get_authorize_uri(from_url, service='calendar', scope=self._get_calendar_scope())

    def _can_authorize_microsoft(self, user):
        return user.has_group('base.group_erp_manager')
