from datetime import date, datetime, UTC
from unittest.mock import patch

from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_calendar import GoogleCalendar
from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.tests.common import tagged


@patch.object(ResUsers, '_get_google_calendar_token', lambda user: 'dummy-token')
@tagged('at_install', '-post_install')
class TestSyncCalendarsGoogle2Odoo(TestSyncGoogle):

    @patch_api
    def test_g2o_new_calendar_is_created_and_does_not_create_duplicate_on_google(self):
        google_calendars = GoogleCalendar([{'id': 'google-new-1', 'summary': 'My New Calendar', 'accessRole': 'owner'}])

        self.organizer_user.calendar_ids.with_user(self.organizer_user)._sync_calendars_google2odoo(google_calendars)

        calendar = self.env['calendar.calendar'].search([('google_id', '=', 'google-new-1')], limit=1)
        self.assertTrue(calendar)
        self.assertEqual(calendar.name, 'My New Calendar')
        self.assertGoogleEventNotInserted()

    def test_g2o_deleted_calendar_is_unlinked(self):
        """
        A GoogleCalendar whose 'deleted' flag is truthy must cause the matching non-primary Odoo record to be removed.
        """
        odoo_cal = self.create_calendar(name='To Delete', google_id='google-del-1')
        google_calendars = GoogleCalendar([{
            'id': 'google-del-1',
            'summary': 'To Delete',
            'deleted': True,
        }])

        self.organizer_user.calendar_ids.with_user(self.organizer_user)._sync_calendars_google2odoo(google_calendars)

        self.assertFalse(odoo_cal.exists(), "Calendar flagged deleted on Google should be removed from Odoo")

    def test_g2o_primary_calendar_is_not_deleted(self):
        """
        The primary Odoo calendar must never be deleted, even if the Google payload somehow marks the calendar as deleted.
        """
        google_calendars = GoogleCalendar([{
            'id': 'primary-gid',
            'summary': 'Primary',
            'deleted': True,
            'primary': True,
        }])

        self.organizer_user.calendar_ids.with_user(self.organizer_user)._sync_calendars_google2odoo(google_calendars)

        self.assertTrue(
            self.organizer_user.primary_calendar.exists(),
            "Primary calendar must never be deleted even when flagged deleted on Google"
        )

    def test_g2o_updated_calendar_writes_changed_fields(self):
        odoo_cal = self.create_calendar(name='Old Name', google_id='google-upd-1', need_sync=False)
        google_calendars = GoogleCalendar([{'id': 'google-upd-1', 'summary': 'New Name From Google'}])

        self.env['calendar.calendar']._sync_calendars_google2odoo(google_calendars)

        self.assertEqual(
            odoo_cal.name, 'New Name From Google',
            "Calendar name should be updated from Google when Odoo has no pending changes",
        )

    def test_g2o_updated_calendar_skips_when_odoo_has_pending_changes(self):
        odoo_cal = self.create_calendar(name='Local Name', google_id='gid', need_sync=True)
        google_calendars = GoogleCalendar([{'id': 'gid', 'summary': 'Google Name'}])

        self.env['calendar.calendar']._sync_calendars_google2odoo(google_calendars)

        self.assertEqual(
            odoo_cal.name, 'Local Name',
            "Calendar with pending local changes should NOT be overwritten by Google",
        )

    @patch_api
    @patch.object(ResUsers, '_sync_request')
    def test_g2o_event_moved_to_a_different_calendar_in_google(self, mock_sync_request):
        # Create an event in the primary calendar
        google_id = '1'
        event = self.env['calendar.event'].with_user(self.organizer_user).create({
            'name': 'Hello world',
            'start': date(2020, 1, 6),
            'stop': date(2020, 1, 6),
            'google_id': google_id,
            'user_id': self.organizer_user.id,
            'need_sync': False,
            'partner_ids': [(6, 0, self.organizer_user.partner_id.ids)]
        })

        # Define mock return values for the '_sync_request' method.
        def mock_sync(google_service, event_id=None, calendar=None):
            if calendar.is_primary:
                return {
                    # Event was removed from the primary calendar
                    'events': GoogleEvent([{'id': google_id, 'status': 'cancelled'}]),
                    'default_reminders': (),
                    'full_sync': False,
                }
            # Event respawned in a secondary calendar
            elif calendar.google_id == self.secondary_calendar.google_id:
                return {
                    'events': GoogleEvent([{
                        'id': google_id,
                        'description': 'desc',
                        "updated": datetime.now().replace(tzinfo=UTC).isoformat(),
                        'organizer': {'email': 'odoocalendarref@gmail.com', 'self': True},
                        'summary': 'Pricing new update',
                        'visibility': 'public',
                        'attendees': [],
                        'reminders': {'useDefault': True},
                        'start': {
                            'dateTime': '2020-01-13T16:55:00+01:00',
                            'timeZone': 'Europe/Brussels'
                        },
                        'end': {
                            'dateTime': '2020-01-13T19:55:00+01:00',
                            'timeZone': 'Europe/Brussels'
                        },
                    }]),
                    'default_reminders': (),
                    'full_sync': False,
                }
            raise Exception("Unexpected calendar")

        mock_sync_request.side_effect = mock_sync
        self.organizer_user.with_user(self.organizer_user)._sync_google_calendar(self.google_service)
        self.assertTrue(event.exists(), "Event should not be deleted because of the move")
        self.assertEqual(event.calendar_id, self.secondary_calendar)
