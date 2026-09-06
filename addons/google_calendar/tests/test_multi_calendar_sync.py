from unittest.mock import patch

from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendar
from odoo.addons.google_calendar.utils.google_calendar_service import GoogleCalendarService
from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, new_test_user


@patch.object(ResUsers, "_get_google_calendar_token", lambda user: "dummy-token")
@tagged("at_install", "-post_install")
class TestMultiCalendarSync(TestSyncGoogle):

    def test_get_google_path_for_own_primary(self):
        """A user's own primary calendar resolves to the special 'primary' path."""
        path = self.organizer_user.primary_calendar_id.with_user(self.organizer_user).get_google_path()
        self.assertEqual(path, "primary")

    def test_get_google_path_for_secondary_is_url_encoded_google_id(self):
        """A secondary calendar resolves to its (url-encoded) google_id."""
        cal = self.create_calendar(name="Encoded", google_id="abc@group.calendar.google.com")
        path = cal.with_user(self.organizer_user).get_google_path()
        self.assertEqual(path, "abc%40group.calendar.google.com")

    def test_get_google_path_for_shared_primary_uses_google_id(self):
        """Another user's primary calendar (shared with me) must use its google_id, not 'primary'."""
        # A calendar that is primary for `attendee_user` but only shared (read) with `organizer_user`.
        self.attendee_user.primary_calendar_id.google_id = "attendee-primary"
        path = self.attendee_user.primary_calendar_id.with_user(self.organizer_user).get_google_path()
        self.assertEqual(path, "attendee-primary")

    @patch.object(GoogleCalendarService, "get_events")
    def test_sync_request_stores_per_calendar_sync_token(self, mock_get_events):
        """A successful events request must persist the returned nextSyncToken on that calendar."""
        # get_events returns (events, next_sync_token, default_reminders).
        mock_get_events.return_value = (GoogleEvent([]), "token-123", ())
        calendar = self.organizer_user.primary_calendar_id
        self.organizer_user.with_user(self.organizer_user)._sync_request(self.google_service, calendar=calendar)
        self.assertEqual(calendar.google_sync_token, "token-123")

    def test_stop_sync_only_clears_users_calendar_tokens(self):
        """Stopping synchronization must clear the user's sync token but leave the other user's token intact."""
        self.organizer_user.primary_calendar_id.google_sync_token = "organizer-token"
        self.env["calendar.user"].sudo().create({
            "calendar_id": self.organizer_user.primary_calendar_id.id,
            "user_id": self.attendee_user.id,
            "access_role": 'reader',
            "google_sync_token": "attendee-token",
        })
        self.env["res.users"].with_user(self.organizer_user).stop_google_synchronization()
        self.assertFalse(self.organizer_user.with_user(self.organizer_user).primary_calendar_id.google_sync_token)
        self.assertTrue(self.organizer_user.with_user(self.attendee_user).primary_calendar_id.google_sync_token)

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
        self.organizer_user.with_user(self.organizer_user)._sync_google_events(self.google_service)
        self.assertIn(self.organizer_user.primary_calendar_id, requested)
        self.assertIn(self.secondary_calendar, requested)

    def test_restart_sync_marks_calendars_for_resync(self):
        """Restarting synchronization must flag the user's calendars as needing a re-sync."""
        self.organizer_user.primary_calendar_id.need_sync = False
        self.env["calendar.calendar"].with_user(self.organizer_user)._restart_google_sync()
        self.assertTrue(self.organizer_user.primary_calendar_id.need_sync)

    def test_shared_calendar_access(self):
        """
        Both owners and writers should be able to create and read all events in a shared calendar.
        Readers cannot create events in the calendar and can only see public events.
        This matches the behavior of Google calendar.
        """
        owner_user = new_test_user(self.env, login='owner-user')
        writer_user = new_test_user(self.env, login='writer-user')
        reader_user = new_test_user(self.env, login='reader-user')
        writer_without_private_access_user = new_test_user(self.env, login='writer-without-private-access-user')
        owner_user.google_account_email = 'o.o@example.com'

        # Calendar was shared on Google, all users now sync it to odoo with their respective access roles
        google_calendars = GoogleCalendar([{'id': 'gid1', 'summary': 'Shared calendar', 'accessRole': 'owner', 'dataOwner': 'o.o@example.com'}])
        owner_user.calendar_ids.with_user(owner_user)._sync_calendars_google2odoo(google_calendars)
        google_calendars = GoogleCalendar([{'id': 'gid1', 'summary': 'Shared calendar', 'accessRole': 'writer'}])
        writer_user.calendar_ids.with_user(writer_user)._sync_calendars_google2odoo(google_calendars)
        google_calendars = GoogleCalendar([{'id': 'gid1', 'summary': 'Shared calendar', 'accessRole': 'reader'}])
        reader_user.calendar_ids.with_user(reader_user)._sync_calendars_google2odoo(google_calendars)
        google_calendars = GoogleCalendar([{'id': 'gid1', 'summary': 'Shared calendar', 'accessRole': 'writerWithoutPrivateAccess'}])
        writer_without_private_access_user.calendar_ids.with_user(writer_without_private_access_user)._sync_calendars_google2odoo(google_calendars)

        # Check that the calendar was created with the correct membership records
        shared_calendar = self.env['calendar.calendar'].search([('google_id', '=', 'gid1')])
        self.assertTrue(shared_calendar)
        self.assertEqual(len(shared_calendar.calendar_user_ids), 4)
        owner_record = shared_calendar.with_user(owner_user).calendar_user_id
        writer_record = shared_calendar.with_user(writer_user).calendar_user_id
        reader_record = shared_calendar.with_user(reader_user).calendar_user_id
        writer_without_private_access_record = shared_calendar.with_user(writer_without_private_access_user).calendar_user_id
        self.assertEqual(owner_record.access_role, 'owner')
        self.assertEqual(writer_record.access_role, 'writer')
        self.assertEqual(reader_record.access_role, 'reader')
        self.assertEqual(writer_without_private_access_record.access_role, 'writer')

        owner_record.google_sync_enabled = True
        self.assertFalse(shared_calendar.with_user(owner_user).is_import_pending)
        self.assertFalse(shared_calendar.with_user(writer_user).is_import_pending)
        self.assertFalse(shared_calendar.with_user(reader_user).is_import_pending)
        self.assertFalse(shared_calendar.with_user(writer_without_private_access_user).is_import_pending)

        # Both the owner and writer should be able to create events in the calendar
        public_event = self.env['calendar.event'].with_user(writer_user).create({'name': 'Event2', 'calendar_id': shared_calendar.id, 'privacy': 'public'})
        private_event = self.env['calendar.event'].with_user(owner_user).create({'name': 'Event1', 'calendar_id': shared_calendar.id, 'privacy': 'private'})

        # Reader should see all public events in the calendar
        public_query = self.env['calendar.event'].with_user(reader_user)._read_group([('id', '=', public_event.id)], groupby=['name'])
        private_query = self.env['calendar.event'].with_user(reader_user)._read_group([('id', '=', private_event.id)], groupby=['name'])
        self.assertTrue(public_query, "Reader should be able to read public events")
        self.assertFalse(private_query, "Reader should not be able to read private events")
        with self.assertRaises(AccessError):
            private_event.with_user(reader_user).write({'name': 'Event-updated'})

        # Writers should be able to write and read all events in the calendar
        public_writer_query = self.env['calendar.event'].with_user(writer_user)._read_group([('id', '=', public_event.id)], groupby=['name'])
        private_writer_query = self.env['calendar.event'].with_user(writer_user)._read_group([('id', '=', private_event.id)], groupby=['name'])
        self.assertTrue(public_writer_query, "Writers and owners should be able to read all events in the calendar")
        self.assertFalse(private_writer_query, "Writers and owners should be able to read all events in the calendar")
        public_event.with_user(writer_user).write({'name': 'Event-updated'})

        owner_private_query = (self.env['calendar.event'].with_user(owner_user)._read_group([('id', '=', private_event.id)], groupby=['name']))
        self.assertTrue(owner_private_query, "Writer without private access should not be able to read private events")
