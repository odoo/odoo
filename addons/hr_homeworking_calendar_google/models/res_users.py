import logging
import datetime
import requests

from odoo import models
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_calendar.models.google_sync import google_calendar_token

_logger = logging.getLogger(__name__)


class User(models.Model):
    _inherit = 'res.users'

    def _sync_working_locations(self, user, calendar_service: GoogleCalendarService, start, end):
        """ Synchronize selected user's working locations from Google Calendar to Odoo. """
        with google_calendar_token(user) as token:
            try:
                return calendar_service.fetch_working_location_events(calendar_service, token, start, end)
            except requests.HTTPError as http_error:
                _logger.error("Error syncing working locations: %s", http_error.response.content)

    def _fetch_week_gevents(self, user):
        """ Get working location events of the selected user for the current week. """
        today = datetime.datetime.combine(datetime.datetime.now(), datetime.datetime.min.time())
        week_start = today - datetime.timedelta(days=today.weekday() + 1)
        week_end = week_start + datetime.timedelta(days=7)
        service = GoogleCalendarService(self.env['google.service'].with_user(user))
        return self._sync_working_locations(user, service, week_start, week_end)

    def cron_sync_working_locations(self):
        """ Synchronize working locations of users with active synchronization. """
        for user in self.env['res.users'].search([]):
            if user.is_google_calendar_synced():
                working_location_gevents = self._fetch_week_gevents(user)
                if working_location_gevents:
                    self.env['calendar.event'].with_user(user)._pre_process_google_events(working_location_gevents)
        return True
