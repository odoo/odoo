import logging
import datetime
import requests

from odoo import api, models
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService
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
            if user.is_google_calendar_synced() and user.with_user(user).primary_calendar_id.google_sync_enabled:
                events = self._fetch_week_gevents(user)
                if events:
                    self.env['calendar.event'].with_user(user)._pre_process_google_events(events)
        return True

    @api.model
    def restart_google_synchronization(self):
        result = super().restart_google_synchronization()
        self.env['hr.employee.location']._restart_google_sync()
        return result

    def _check_pending_odoo_records(self):
        return super()._check_pending_odoo_records() or (
            self._get_google_sync_status() == 'sync_active'
            and self.primary_calendar_id.google_sync_enabled
            and self.env['hr.employee.location']._check_any_records_to_sync()
        )

    def _sync_google_events(self, calendar_service):
        result = super()._sync_google_events(calendar_service)
        if self._get_google_sync_status() != 'sync_active':
            return result
        locations = self.env['hr.employee.location']._get_records_to_sync(self.primary_calendar_id)
        locations.with_context(send_updates=False)._sync_odoo2google(calendar_service)
        return result or bool(locations)
