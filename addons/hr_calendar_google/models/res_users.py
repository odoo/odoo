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

        # Fetch the user's language or fallback to the environment default.
        lang_code = user.lang or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)

        # Determine the start of the week based on the language.
        lang_week_start = int(lang.week_start or '7') - 1

        days_to_subtract = (today.weekday() - lang_week_start) % 7
        week_start = today - datetime.timedelta(days=days_to_subtract)
        week_end = week_start + datetime.timedelta(days=7)

        service = GoogleCalendarService(self.env['google.service'].with_user(user))
        with google_calendar_token(user) as token:
            try:
                events, _, _ = service.get_events(
                    token=token,
                    search_params={
                        'timeMin': week_start.isoformat() + 'Z',
                        'timeMax': week_end.isoformat() + 'Z',
                        'eventTypes': ['workingLocation'],
                        'singleEvents': True,
                    }
                )
                return events
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

    def restart_google_synchronization(self):
        result = super().restart_google_synchronization()
        self.env['hr.employee.location']._restart_google_sync()
        return result

    def _check_pending_odoo_records(self):
        return super()._check_pending_odoo_records() or self.env['hr.employee.location']._check_any_records_to_sync()

    def _sync_google_calendar(self, calendar_service):
        result = super()._sync_google_calendar(calendar_service)
        for user in self:
            locations = self.env['hr.employee.location'].with_user(user)._get_records_to_sync()
            locations.with_context(send_updates=False)._sync_odoo2google(calendar_service)
            result = result or bool(locations)
        return result
