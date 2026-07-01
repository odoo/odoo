from datetime import datetime
from unittest.mock import patch

from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.tests.common import tagged


@patch.object(ResUsers, '_get_google_calendar_token', lambda user: 'dummy-token')
@tagged('at_install', '-post_install')
class TestSyncCalendarsGoogle2Odoo(TestSyncGoogle):

    @patch_api
    def test_o2g_skip_when_sync_not_active(self):
        """Nothing must be sent to Google when the user's sync status is not sync_active."""
        self.organizer_user.pause_google_synchronization()
        cal = self.create_calendar(name='My Calendar', need_sync=True)
        cal._sync_calendars_odoo2google(self.google_service)
        self.assertGoogleAPINotCalled()

    @patch_api
    def test_o2g_new_non_primary_calendar_calls_insert(self):
        """Creating a new calendar must call _google_calendar_insert."""
        cal = self.create_calendar(name='New Calendar')
        self.assertGoogleCalendarInserted(cal._google_values())

    @patch_api
    def test_o2g_existing_synced_calendar_calls_patch(self):
        """Editing synchronized calendar must call _google_calendar_patch."""
        self.organizer_user.primary_calendar._sync_calendars_odoo2google(self.google_service)
        self.organizer_user.primary_calendar.name = 'New Name'
        self.assertGoogleCalendarPatched(
            self.organizer_user.primary_calendar.id,
            self.organizer_user.primary_calendar._google_values()
        )

    @patch_api
    def test_o2g_moving_calendar_in_odoo_moves_event_in_google(self):
        # Create an event in the primary calendar
        google_id = '1'
        event = self.env['calendar.event'].with_user(self.organizer_user).create({
            'name': 'Hello world',
            'google_id': google_id,
            'user_id': self.organizer_user.id,
            'need_sync': False,
            'partner_ids': [(6, 0, self.organizer_user.partner_id.ids)]
        })
        # Move the event and assert that the move was called
        event.calendar_id = self.secondary_calendar
        self.assertGoogleEventMoved(google_id, "primary", self.secondary_calendar.google_id)
        event.calendar_id = self.organizer_user.primary_calendar
        self.assertGoogleEventMoved(google_id, self.secondary_calendar.google_id, "primary")

    @patch_api
    @patch.object(ResUsers, '_sync_request')
    def test_o2g_moving_calendar_in_odoo_when_paused_moves_event_in_google_after_unpause(self, mock_sync_request):
        google_id = '2'
        event = self.env['calendar.event'].with_user(self.organizer_user).create({
            'name': 'Hello world',
            'google_id': google_id,
            'user_id': self.organizer_user.id,
            'need_sync': False,
            'partner_ids': [(6, 0, self.organizer_user.partner_id.ids)]
        })

        # Define mock return values for the '_sync_request' method.
        mock_sync_request.return_value = {
            'events': GoogleEvent([]),
            'default_reminders': (),
            'full_sync': False,
        }

        # Pause the synchronization and move the event
        self.organizer_user.sudo().pause_google_synchronization()
        event.calendar_id = self.secondary_calendar

        # With the synchronization paused, manually call the synchronization to simulate the page refresh.
        self.organizer_user.sudo()._sync_google_calendar(self.google_service)
        self.assertGoogleEventNotMoved()

        # Unpause and call the calendar synchronization. Ensure the event was moved on Google side.
        self.organizer_user.sudo().unpause_google_synchronization()
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_google_calendar(self.google_service)
        self.assertGoogleEventMoved(google_id, "primary", self.secondary_calendar.google_id)

    @patch_api
    def test_o2g_changing_calendar_organizer_removes_and_recreates_calendar_in_google(self):
        google_id = '3'
        event = self.env['calendar.event'].with_user(self.organizer_user).create({
            'name': 'Event',
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
            'google_id': google_id,
            'user_id': self.organizer_user.id,
            'need_sync': True,
            'partner_ids': [(6, 0, self.organizer_user.partner_id.ids)]
        })
        insert_common_data = {
            'start': {'dateTime': '2020-01-15T08:00:00+00:00', 'date': None},
            'end': {'dateTime': '2020-01-15T18:00:00+00:00', 'date': None},
            'summary': 'Event',
            'description': event.description,
            'location': '',
            'guestsCanModify': True,
            'extendedProperties': {'shared': {'%s_odoo_id' % self.env.cr.dbname: event.id}},
            'reminders': {'overrides': [{'method': 'popup', 'minutes': 15}], 'useDefault': False},
            'attendees': [{'email': 'o.o@example.com', 'responseStatus': 'accepted'}],
            'conferenceData': None,
            'transparency': 'opaque',
        }
        self.assertGoogleEventInserted({
            'id': '3',
            'organizer': {'email': 'o.o@example.com', 'self': True},
            **insert_common_data,
        })

        google_id = event.google_id
        event.user_id = self.attendee_user
        self.assertGoogleEventDeleted(google_id)
        self.assertFalse(event.google_id)
        self.assertEqual(event.calendar_id, self.attendee_user.primary_calendar)

        # Event should be inserted again
        event._sync_odoo2google(self.google_service)
        self.assertEqual(len(self._gsync_insert_values), 2)
