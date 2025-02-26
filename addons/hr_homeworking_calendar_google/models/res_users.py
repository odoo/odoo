import logging
import datetime
import requests

from odoo import models
from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_calendar.models.google_sync import google_calendar_token

_logger = logging.getLogger(__name__)


def fetch_working_location_events(google_service: GoogleCalendarService, token, start, end, timeout=3):
    """ Get working location events from Google Calendar. """
    url = "/calendar/v3/calendars/primary/events"
    headers = {'Content-type': 'application/json'}
    params = {
        'access_token': token,
        'timeMin': start.isoformat() + 'Z',
        'timeMax': end.isoformat() + 'Z',
        'eventTypes': ['workingLocation'],
    }

    events = []
    while True:
        _, data, _ = google_service.google_service._do_request(url, params, headers, method='GET', timeout=timeout)
        events.extend(data.get('items', []))
        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break
        params['pageToken'] = next_page_token

    return GoogleEvent(events)


class User(models.Model):
    _inherit = 'res.users'

    def sync_working_locations(self, user, calendar_service: GoogleCalendarService, start, end):
        """ Synchronize selected user's working locations from Google Calendar to Odoo. """
        self.env.cr.execute("""SELECT id FROM res_users WHERE id = %s FOR NO KEY UPDATE SKIP LOCKED""", [user.id])
        if not self.env.cr.rowcount:
            _logger.info("Skipping sync, locked user %s", self.login)
            return False

        with google_calendar_token(user) as token:
            try:
                return fetch_working_location_events(calendar_service, token, start, end)
            except requests.HTTPError as http_error:
                _logger.error("Error syncing working locations: %s", http_error.response.content)

    def fetch_week_gevents(self, user):
        """ Get working location events of the selected user for the current week. """
        today = datetime.datetime.combine(datetime.datetime.now(), datetime.datetime.min.time())
        week_start = today - datetime.timedelta(days=today.weekday() + 1)
        week_end = week_start + datetime.timedelta(days=7)
        service = GoogleCalendarService(self.env['google.service'].with_user(user))
        return self.sync_working_locations(user, service, week_start, week_end)

    def cron_sync_working_locations(self):
        """ Synchronize working locations of users with active synchronization. """
        for user in self.env['res.users'].search([]):
            if user.is_google_calendar_synced():
                working_location_gevents = self.fetch_week_gevents(user)
                if working_location_gevents:
                    self.env['calendar.event'].with_user(user)._pre_process_google_events(working_location_gevents)
        return True
