import logging
import datetime
import requests

from odoo import models
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendarService
from odoo.addons.google_calendar.models.google_sync import google_calendar_token

_logger = logging.getLogger(__name__)


class User(models.Model):
    _inherit = 'res.users'

    def _fetch_week_gevents(self, user):
        """ Get working location events of the selected user for the current week. """
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today - datetime.timedelta(days=today.weekday() + 1)
        week_end = week_start + datetime.timedelta(days=7)

        service = GoogleCalendarService(self.env['google.service'].with_user(user))
        with google_calendar_token(user) as token:
            try:
                return service.fetch_working_location_events(token=token, start=week_start, end=week_end)
            except requests.HTTPError as e:
                _logger.error("Error syncing working locations: %s", e.response.content)
                return []

    def cron_sync_working_locations(self):
        """ Synchronize working locations of users with active synchronization. """
        # Optimization: Only search users with a valid token
        users = self.search([('google_calendar_token', '!=', False)])
        for user in users:
            if user.is_google_calendar_synced():
                events = self._fetch_week_gevents(user)
                if events:
                    self.env['calendar.event'].with_user(user)._pre_process_google_events(events)
        return True
