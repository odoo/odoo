from unittest.mock import patch

from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService
from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.tests.common import tagged


@patch.object(ResUsers, "_get_google_calendar_token", lambda user: "dummy-token")
@tagged("at_install", "-post_install")
class TestMultiCalendarSync(TestSyncGoogle):

    def test_get_google_path_for_own_primary(self):
        """A user's own primary calendar resolves to the special 'primary' path."""
        path = self.organizer_user.primary_calendar.with_user(self.organizer_user).get_google_path()
        self.assertEqual(path, "primary")

    def test_get_google_path_for_secondary_is_url_encoded_google_id(self):
        """A secondary calendar resolves to its (url-encoded) google_id."""
        cal = self.create_calendar(name="Encoded", google_id="abc@group.calendar.google.com")
        path = cal.with_user(self.organizer_user).get_google_path()
        self.assertEqual(path, "abc%40group.calendar.google.com")

    def test_get_google_path_for_shared_primary_uses_google_id(self):
        """Another user's primary calendar (shared with me) must use its google_id, not 'primary'."""
        # A calendar that is primary for `attendee_user` but only shared (read) with `organizer_user`.
        self.attendee_user.primary_calendar.google_id = "attendee-primary"
        path = self.attendee_user.primary_calendar.with_user(self.organizer_user).get_google_path()
        self.assertEqual(path, "attendee-primary")

    @patch.object(GoogleCalendarService, "get_events")
    def test_sync_request_stores_per_calendar_sync_token(self, mock_get_events):
        """A successful events request must persist the returned nextSyncToken on that calendar."""
        # get_events returns (events, next_sync_token, default_reminders).
        mock_get_events.return_value = (GoogleEvent([]), "token-123", ())
        calendar = self.organizer_user.primary_calendar
        self.organizer_user.with_user(self.organizer_user)._sync_request(self.google_service, calendar=calendar)
        self.assertEqual(calendar.google_sync_token, "token-123")

    def test_stop_sync_clears_per_calendar_tokens(self):
        """Stopping synchronization must clear every calendar's individual sync token."""
        self.organizer_user.primary_calendar.google_sync_token = "to-be-cleared"
        self.env["res.users"].with_user(self.organizer_user).stop_google_synchronization()
        self.assertFalse(self.organizer_user.primary_calendar.google_sync_token)

    @patch_api
    @patch.object(ResUsers, "_sync_request")
    def test_events_sync_iterates_over_all_user_calendars(self, mock_sync_request):
        """The events sync must issue a request for each of the user's calendars."""
        requested = []

        def _record(service, event_id=None, calendar=None):
            # Remember which calendars were queried, then return an empty result set.
            requested.append(calendar)
            return {"events": GoogleEvent([]), "default_reminders": (), "full_sync": False}

        mock_sync_request.side_effect = _record
        self.organizer_user.with_user(self.organizer_user)._sync_google_calendar(self.google_service)
        self.assertIn(self.organizer_user.primary_calendar, requested)
        self.assertIn(self.secondary_calendar, requested)

    def test_restart_sync_marks_calendars_for_resync(self):
        """Restarting synchronization must flag the user's calendars as needing a re-sync."""
        self.organizer_user.primary_calendar.need_sync = False
        self.env["calendar.calendar"].with_user(self.organizer_user)._restart_google_sync()
        self.assertTrue(self.organizer_user.primary_calendar.need_sync)
