from unittest.mock import patch, call
from datetime import timedelta, datetime
from freezegun import freeze_time

from odoo import Command, fields

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.models.res_users import User
from odoo.addons.microsoft_calendar.tests.common import TestCommon, mock_get_token, _modified_date_in_the_future
from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
@patch.object(User, '_get_microsoft_calendar_token', mock_get_token)
class TestCreateEvents(TestCommon):

    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_simple_event_without_sync(self, mock_insert):
        """
        A Odoo event is created when Outlook sync is not enabled.
        """

        # arrange
        self.organizer_user.microsoft_synchronization_stopped = True

        # act
        record = self.env["calendar.event"].with_user(self.organizer_user).create(self.simple_event_values)
        self.call_post_commit_hooks()
        record.invalidate_recordset()

        # assert
        mock_insert.assert_not_called()
        self.assertEqual(record.need_sync_m, False)

    def test_create_simple_event_without_email(self):
        """
        Outlook does not accept attendees without email.
        """
        # arrange
        self.attendee_user.partner_id.email = False

        # act & assert
        record = self.env["calendar.event"].with_user(self.organizer_user).create(self.simple_event_values)

        with self.assertRaises(ValidationError):
            record._sync_odoo2microsoft()

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_create_simple_event_from_outlook_organizer_calendar(self, mock_get_events):
        """
        An event has been created in Outlook and synced in the Odoo organizer calendar.
        """

        # arrange
        mock_get_events.return_value = (MicrosoftEvent([self.simple_event_from_outlook_organizer]), None)
        existing_records = self.env["calendar.event"].search([])

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        records = self.env["calendar.event"].search([])
        new_records = (records - existing_records)
        self.assertEqual(len(new_records), 1)
        self.assert_odoo_event(new_records, self.expected_odoo_event_from_outlook)
        self.assertEqual(new_records.user_id, self.organizer_user)
        self.assertEqual(new_records.need_sync_m, False)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_create_simple_event_from_outlook_attendee_calendar_and_organizer_exists_in_odoo(self, mock_get_events):
        """
        An event has been created in Outlook and synced in the Odoo attendee calendar.
        There is a Odoo user that matches with the organizer email address.
        """

        # arrange
        mock_get_events.return_value = (MicrosoftEvent([self.simple_event_from_outlook_attendee]), None)
        existing_records = self.env["calendar.event"].search([])

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        records = self.env["calendar.event"].search([])
        new_records = (records - existing_records)
        self.assertEqual(len(new_records), 1)
        self.assert_odoo_event(new_records, self.expected_odoo_event_from_outlook)
        self.assertEqual(new_records.user_id, self.organizer_user)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_create_simple_event_from_outlook_attendee_calendar_and_organizer_does_not_exist_in_odoo(self, mock_get_events):
        """
        An event has been created in Outlook and synced in the Odoo attendee calendar.
        no Odoo user that matches with the organizer email address.
        """

        # arrange
        outlook_event = self.simple_event_from_outlook_attendee
        outlook_event = dict(self.simple_event_from_outlook_attendee, organizer={
            'emailAddress': {'address': "john.doe@odoo.com", 'name': "John Doe"},
        })
        expected_event = dict(self.expected_odoo_event_from_outlook, user_id=False)

        mock_get_events.return_value = (MicrosoftEvent([outlook_event]), None)
        existing_records = self.env["calendar.event"].search([])

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        records = self.env["calendar.event"].search([])
        new_records = (records - existing_records)
        self.assertEqual(len(new_records), 1)
        self.assert_odoo_event(new_records, expected_event)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_create_simple_event_from_outlook_attendee_calendar_where_email_addresses_are_capitalized(self, mock_get_events):
        """
        An event has been created in Outlook and synced in the Odoo attendee calendar.
        The email addresses of the attendee and the organizer are in different case than in Odoo.
        """

        # arrange
        outlook_event = dict(self.simple_event_from_outlook_attendee, organizer={
            'emailAddress': {'address': "Mike@organizer.com", 'name': "Mike Organizer"},
        }, attendees=[{'type': 'required', 'status': {'response': 'none', 'time': '0001-01-01T00:00:00Z'},
                       'emailAddress': {'name': 'John Attendee', 'address': 'John@attendee.com'}}])

        mock_get_events.return_value = (MicrosoftEvent([outlook_event]), None)
        existing_records = self.env["calendar.event"].search([])

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        records = self.env["calendar.event"].search([])
        new_records = (records - existing_records)
        self.assertEqual(len(new_records), 1)
        self.assert_odoo_event(new_records, self.expected_odoo_event_from_outlook)
        self.assertEqual(new_records.user_id, self.organizer_user)

    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_recurrent_event_without_sync(self, mock_insert):
        """
        A Odoo recurrent event is created when Outlook sync is not enabled.
        """
        if not self.sync_odoo_recurrences_with_outlook_feature():
            return

        # arrange
        self.organizer_user.microsoft_synchronization_stopped = True

        # act
        record = self.env["calendar.event"].with_user(self.organizer_user).create(self.recurrent_event_values)
        self.call_post_commit_hooks()
        record.invalidate_recordset()

        # assert
        mock_insert.assert_not_called()
        self.assertEqual(record.need_sync_m, False)

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_recurrent_event_with_sync(self, mock_insert, mock_get_events):
        """
        A Odoo recurrent event is created when Outlook sync is enabled.
        """
        if not self.sync_odoo_recurrences_with_outlook_feature():
            return

        # >>> first phase: create the recurrence

        # act
        record = self.env["calendar.event"].with_user(self.organizer_user).create(self.recurrent_event_values)

        # assert
        recurrence = self.env["calendar.recurrence"].search([("base_event_id", "=", record.id)])

        mock_insert.assert_not_called()
        self.assertEqual(record.name, "recurring_event")
        self.assertEqual(recurrence.name, "Every 2 Days for 7 events")
        self.assertEqual(len(recurrence.calendar_event_ids), 7)

        # >>> second phase: sync with organizer outlook calendar

        # arrange
        event_id = "123"
        event_iCalUId = "456"
        mock_insert.return_value = (event_id, event_iCalUId)
        mock_get_events.return_value = ([], None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()
        self.call_post_commit_hooks()
        recurrence.invalidate_recordset()

        # assert
        self.assertEqual(recurrence.microsoft_id, event_id)
        self.assertEqual(recurrence.ms_universal_event_id, event_iCalUId)
        self.assertEqual(recurrence.need_sync_m, False)

        mock_insert.assert_called_once()
        self.assert_dict_equal(mock_insert.call_args[0][0], self.recurrent_event_ms_values)

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_recurrent_event_with_sync_by_another_user(self, mock_insert, mock_get_events):
        """
        A Odoo recurrent event has been created and synced with Outlook by another user, but nothing
        should happen as it we prevent sync of recurrences from other users
        ( see microsoft_calendar/models/calendar_recurrence_rule.py::_get_microsoft_sync_domain() )
        """
        if not self.sync_odoo_recurrences_with_outlook_feature():
            return
        # >>> first phase: create the recurrence

        # act
        record = self.env["calendar.event"].with_user(self.organizer_user).create(self.recurrent_event_values)

        # assert
        recurrence = self.env["calendar.recurrence"].search([("base_event_id", "=", record.id)])

        mock_insert.assert_not_called()
        self.assertEqual(record.name, "recurring_event")
        self.assertEqual(recurrence.name, f"Every 2 Days for {self.recurrent_events_count} events")
        self.assertEqual(len(recurrence.calendar_event_ids), self.recurrent_events_count)

        # >>> second phase: sync with attendee Outlook calendar

        # arrange
        event_id = "123"
        event_iCalUId = "456"
        mock_insert.return_value = (event_id, event_iCalUId)
        mock_get_events.return_value = ([], None)

        # act
        self.attendee_user.with_user(self.attendee_user).sudo()._sync_microsoft_calendar()
        self.call_post_commit_hooks()
        recurrence.invalidate_recordset()

        # assert
        mock_insert.assert_not_called()

        self.assertEqual(recurrence.microsoft_id, False)
        self.assertEqual(recurrence.ms_universal_event_id, False)
        self.assertEqual(recurrence.need_sync_m, False)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_create_recurrent_event_from_outlook_organizer_calendar(self, mock_get_events):
        """
        A recurrent event has been created in Outlook and synced in the Odoo organizer calendar.
        """

        # arrange
        mock_get_events.return_value = (MicrosoftEvent(self.recurrent_event_from_outlook_organizer), None)
        existing_events = self.env["calendar.event"].search([])
        existing_recurrences = self.env["calendar.recurrence"].search([])

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        new_events = (self.env["calendar.event"].search([]) - existing_events)
        new_recurrences = (self.env["calendar.recurrence"].search([]) - existing_recurrences)
        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(len(new_events), self.recurrent_events_count)
        self.assert_odoo_recurrence(new_recurrences, self.expected_odoo_recurrency_from_outlook)
        for i, e in enumerate(sorted(new_events, key=lambda e: e.id)):
            self.assert_odoo_event(e, self.expected_odoo_recurrency_events_from_outlook[i])

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_create_recurrent_event_from_outlook_attendee_calendar(self, mock_get_events):
        """
        A recurrent event has been created in Outlook and synced in the Odoo attendee calendar.
        """

        # arrange
        mock_get_events.return_value = (MicrosoftEvent(self.recurrent_event_from_outlook_attendee), None)
        existing_events = self.env["calendar.event"].search([])
        existing_recurrences = self.env["calendar.recurrence"].search([])

        # act
        self.attendee_user.with_user(self.attendee_user).sudo()._sync_microsoft_calendar()

        # assert
        new_events = (self.env["calendar.event"].search([]) - existing_events)
        new_recurrences = (self.env["calendar.recurrence"].search([]) - existing_recurrences)
        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(len(new_events), self.recurrent_events_count)
        self.assert_odoo_recurrence(new_recurrences, self.expected_odoo_recurrency_from_outlook)
        for i, e in enumerate(sorted(new_events, key=lambda e: e.id)):
            self.assert_odoo_event(e, self.expected_odoo_recurrency_events_from_outlook[i])

    @patch.object(MicrosoftCalendarService, 'insert')
    def test_forbid_recurrences_creation_synced_outlook_calendar(self, mock_insert):
        """
        Forbids new recurrences creation in Odoo due to Outlook spam limitation of updating recurrent events.
        """
        # Set custom calendar token validity to simulate real scenario.
        self.env.user.microsoft_calendar_token_validity = datetime.now() + timedelta(minutes=5)

        # Assert that synchronization with Outlook is active.
        self.assertFalse(self.env.user.microsoft_synchronization_stopped)

        with self.assertRaises(UserError):
            self.env["calendar.event"].create(
                self.recurrent_event_values
            )
        # Assert that no insert call was made.
        mock_insert.assert_not_called()

    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_event_with_sync_config_paused(self, mock_insert):
        """
        Creates an event with the synchronization paused, the event must have its field 'need_sync_m' as True
        for later synchronizing it with Outlook Calendar.
        """
        # Set user sync configuration as active and then pause the synchronization.
        self.organizer_user.microsoft_synchronization_stopped = False
        self.organizer_user.pause_microsoft_synchronization()

        # Try to create a simple event in Odoo Calendar.
        record = self.env["calendar.event"].with_user(self.organizer_user).create(self.simple_event_values)
        self.call_post_commit_hooks()
        record.invalidate_recordset()

        # Ensure that synchronization is paused, insert wasn't called and record is waiting to be synced.
        self.assertFalse(self.organizer_user.microsoft_synchronization_stopped)
        self.assertEqual(self.organizer_user._get_microsoft_sync_status(), "sync_paused")
        self.assertTrue(record.need_sync_m, "Sync variable must be true for updating event when sync re-activates")
        mock_insert.assert_not_called()

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_sync_create_update_single_event(self, mock_insert, mock_get_events):
        """
        If the synchronization with Outlook is stopped, then records (events and recurrences) created or updated
        should not be synced. They must be synced only when created or updated having the synchronization active.
        In this test, the synchronization is stopped and an event is created locally. After this, the synchronization
        is restarted and the event is updated (this way, syncing it with Outlook Calendar).
        """
        # Set last synchronization date for allowing synchronizing events created after this date.
        self.organizer_user._set_ICP_first_synchronization_date(fields.Datetime.now())

        # Stop the synchronization for clearing the last_sync_date.
        self.organizer_user.with_user(self.organizer_user).sudo().stop_microsoft_synchronization()
        self.assertEqual(self.organizer_user.microsoft_last_sync_date, False,
                         "Variable last_sync_date must be False due to sync stop.")

        # Create a not synced event (local).
        simple_event_values_updated = self.simple_event_values
        for date_field in ['start', 'stop']:
            simple_event_values_updated[date_field] = simple_event_values_updated[date_field].replace(year=datetime.now().year)
        event = self.env["calendar.event"].with_user(self.organizer_user).create(simple_event_values_updated)

        # Assert that insert was not called and prepare mock for the synchronization restart.
        mock_insert.assert_not_called()
        mock_get_events.return_value = ([], None)

        ten_minutes_after_creation = event.write_date + timedelta(minutes=10)
        with freeze_time(ten_minutes_after_creation):
            # Restart the synchronization with Outlook Calendar.
            self.organizer_user.with_user(self.organizer_user).sudo().restart_microsoft_synchronization()
            # Sync microsoft calendar, considering that ten minutes were passed after the event creation.
            self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()
            self.call_post_commit_hooks()
            event.invalidate_recordset()

            # Assert that insert function was not called and check last_sync_date variable value.
            mock_insert.assert_not_called()

            self.assertNotEqual(self.organizer_user.microsoft_last_sync_date, False,
                                "Variable last_sync_date must not be empty after sync.")
            self.assertLessEqual(event.write_date, self.organizer_user.microsoft_last_sync_date,
                                "Event creation must happen before last_sync_date")

            # Assert that the local event did not get synced after synchronization restart.
            self.assertEqual(event.microsoft_id, False,
                            "Event should not be synchronized while sync is paused.")
            self.assertEqual(event.ms_universal_event_id, False,
                            "Event should not be synchronized while sync is paused.")

        # Update local event information.
        event.write({
            "name": "New event name"
        })
        self.call_post_commit_hooks()

        # Prepare mock for new synchronization.
        event_id = "123"
        event_iCalUId = "456"
        mock_insert.return_value = (event_id, event_iCalUId)
        mock_get_events.return_value = ([], None)

        # Synchronize local event with Outlook after updating it locally.
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()
        self.call_post_commit_hooks()
        event.invalidate_recordset()

        # Assert that the event got synchronized with Microsoft (through mock).
        self.assertEqual(event.microsoft_id, "123")
        self.assertEqual(event.ms_universal_event_id, "456")

        # Assert that the Microsoft Insert was called once.
        mock_insert.assert_called_once()

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_event_for_another_user(self, mock_insert, mock_get_events):
        """
        Allow the creation of event for another user only if the proposed user have its Odoo Calendar synced.
        User A (self.organizer_user) is creating an event with user B as organizer (self.attendee_user).
        """
        # Ensure that the calendar synchronization of user A is active. Deactivate user B synchronization for throwing an error.
        self.assertTrue(self.env['calendar.event'].with_user(self.organizer_user)._check_microsoft_sync_status())
        self.attendee_user.microsoft_synchronization_stopped = True

        # Try creating an event with the organizer as the user B (self.attendee_user).
        # A ValidationError must be thrown because user B's calendar is not synced.
        self.simple_event_values['user_id'] = self.attendee_user.id
        self.simple_event_values['partner_ids'] = [Command.set([self.organizer_user.partner_id.id])]
        with self.assertRaises(ValidationError):
            self.env['calendar.event'].with_user(self.organizer_user).create(self.simple_event_values)

        # Activate the calendar synchronization of user B (self.attendee_user).
        self.attendee_user.microsoft_synchronization_stopped = False
        self.assertTrue(self.env['calendar.event'].with_user(self.attendee_user)._check_microsoft_sync_status())

        # Try creating an event with organizer as the user B but not inserting B as an attendee. A ValidationError must be thrown.
        with self.assertRaises(ValidationError):
            self.env['calendar.event'].with_user(self.organizer_user).create(self.simple_event_values)

        # Set mock return values for the event creation.
        event_id = "123"
        event_iCalUId = "456"
        mock_insert.return_value = (event_id, event_iCalUId)
        mock_get_events.return_value = ([], None)

        # Create event matching the creation conditions: user B is synced and now listed as an attendee. Set mock return values.
        self.simple_event_values['partner_ids'] = [Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])]
        event = self.env['calendar.event'].with_user(self.organizer_user).create(self.simple_event_values)
        self.call_post_commit_hooks()
        event.invalidate_recordset()

        # Ensure that event was inserted and user B (self.attendee_user) is the organizer and is also listed as attendee.
        mock_insert.assert_called_once()
        self.assertEqual(event.user_id, self.attendee_user, "Event organizer must be user B (self.attendee_user) after event creation by user A (self.organizer_user).")
        self.assertTrue(self.attendee_user.partner_id.id in event.partner_ids.ids, "User B (self.attendee_user) should be listed as attendee after event creation.")

        # Try creating an event with portal user (with no access rights) as organizer from Microsoft.
        # In Odoo, this event will be created (behind the screens) by a synced Odoo user as attendee (self.attendee_user).
        portal_group = self.env.ref('base.group_portal')
        portal_user = self.env['res.users'].create({
            'login': 'portal@user',
            'email': 'portal@user',
            'name': 'PortalUser',
            'groups_id': [Command.set([portal_group.id])],
            })

        # Mock event from Microsoft and sync event with Odoo through self.attendee_user (synced user).
        self.simple_event_from_outlook_organizer.update({
            'id': 'portalUserEventID',
            'iCalUId': 'portalUserEventICalUId',
            'organizer': {'emailAddress': {'address': portal_user.login, 'name': portal_user.name}},
        })
        mock_get_events.return_value = (MicrosoftEvent([self.simple_event_from_outlook_organizer]), None)
        self.assertTrue(self.env['calendar.event'].with_user(self.attendee_user)._check_microsoft_sync_status())
        self.attendee_user.with_user(self.attendee_user).sudo()._sync_microsoft_calendar()

        # Ensure that event was successfully created in Odoo (no ACL error was triggered blocking creation).
        portal_user_events = self.env['calendar.event'].search([('user_id', '=', portal_user.id)])
        self.assertEqual(len(portal_user_events), 1)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_create_simple_event_from_outlook_without_organizer(self, mock_get_events):
        """
        Allow creation of an event without organizer in Outlook and sync it in Odoo.
        """

        # arrange
        outlook_event = self.simple_event_from_outlook_attendee
        outlook_event = dict(self.simple_event_from_outlook_attendee, organizer=None)
        expected_event = dict(self.expected_odoo_event_from_outlook, user_id=False)

        mock_get_events.return_value = (MicrosoftEvent([outlook_event]), None)
        existing_records = self.env["calendar.event"].search([])

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        records = self.env["calendar.event"].search([])
        new_records = (records - existing_records)
        self.assertEqual(len(new_records), 1)
        self.assert_odoo_event(new_records, expected_event)

    def test_create_event_with_default_and_undefined_sensitivity(self):
        """ Check if microsoft events are created in Odoo when 'None' sensitivity setting is defined and also when it is not. """
        # Sync events from Microsoft to Odoo after adding the sensitivity (privacy) property.
        self.simple_event_from_outlook_organizer.pop('sensitivity')
        undefined_privacy_event = {'id': 100, 'iCalUId': 2, **self.simple_event_from_outlook_organizer}
        default_privacy_event = {'id': 200, 'iCalUId': 4, 'sensitivity': None, **self.simple_event_from_outlook_organizer}
        self.env['calendar.event']._sync_microsoft2odoo(MicrosoftEvent([undefined_privacy_event, default_privacy_event]))

        # Ensure that synced events have the correct privacy field in Odoo.
        undefined_privacy_odoo_event = self.env['calendar.event'].search([('microsoft_id', '=', 100)])
        default_privacy_odoo_event = self.env['calendar.event'].search([('microsoft_id', '=', 200)])
        self.assertFalse(undefined_privacy_odoo_event.privacy, "Event with undefined privacy must have False value in privacy field.")
        self.assertFalse(default_privacy_odoo_event.privacy, "Event with custom privacy must have False value in privacy field.")

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_videocall_sync_microsoft_calendar(self, mock_insert, mock_get_events):
        """
        Test syncing an event from Odoo to Microsoft Calendar.
        Ensures that meeting details are correctly updated after syncing from Microsoft.
        """
        record = self.env["calendar.event"].with_user(self.organizer_user).create(self.simple_event_values)
        self.assertEqual(record.name, "simple_event", "Event name should be same as simple_event")

        # Mock values to simulate Microsoft event creation
        event_id = "123"
        event_iCalUId = "456"
        mock_insert.return_value = (event_id, event_iCalUId)

        # Prepare the mock event response from Microsoft
        self.response_from_outlook_organizer = {
            **self.simple_event_from_outlook_organizer,
            '_odoo_id': record.id,
            'onlineMeeting': {
                'joinUrl': 'https://teams.microsoft.com/l/meetup-join/test',
                'conferenceId': '275984951',
                'tollNumber': '+1 323-555-0166',
            },
            'lastModifiedDateTime': _modified_date_in_the_future(record),
            'isOnlineMeeting': True,
            'onlineMeetingProvider': 'teamsForBusiness',
        }
        mock_get_events.return_value = (MicrosoftEvent([self.response_from_outlook_organizer]), None)
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()
        self.call_post_commit_hooks()
        record.invalidate_recordset()

        # Check that Microsoft insert was called exactly once
        mock_insert.assert_called_once()
        self.assertEqual(record.microsoft_id, event_id, "The Microsoft ID should be assigned to the event.")
        self.assertEqual(record.ms_universal_event_id, event_iCalUId)
        self.assertEqual(mock_insert.call_args[0][0].get('isOnlineMeeting'), True,
                         "The event should be marked as an online meeting.")
        self.assertEqual(mock_insert.call_args[0][0].get('onlineMeetingProvider'), 'teamsForBusiness',
                         "The event's online meeting provider should be set to Microsoft Teams.")
        self.assertEqual(record.need_sync_m, False)

        # Verify the event's videocall_location is updated in Odoo
        event = self.env['calendar.event'].search([('name', '=', self.response_from_outlook_organizer.get('subject'))])
        self.assertTrue(event, "The event should exist in the calendar after sync.")
        self.assertEqual(event.videocall_location, 'https://teams.microsoft.com/l/meetup-join/test', "The meeting URL should match.")

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_no_videocall_hr_holidays(self, mock_insert, mock_get_events):
        """
        Test HR holidays synchronization with Microsoft Calendar, ensuring no online meetings
        are generated for leave requests.
        """
        # Skip test if HR Holidays module isn't installed
        if self.env['ir.module.module']._get('hr_holidays').state not in ['installed', 'to upgrade']:
            self.skipTest("The 'hr_holidays' module must be installed to run this test.")

        self.user_hrmanager = mail_new_test_user(self.env, login='bastien', groups='base.group_user,hr_holidays.group_hr_holidays_manager')
        self.user_employee = mail_new_test_user(self.env, login='enguerran', password='enguerran', groups='base.group_user')
        self.rd_dept = self.env['hr.department'].with_context(tracking_disable=True).create({
            'name': 'Research and Development',
        })
        self.employee_emp = self.env['hr.employee'].create({
            'name': 'Marc Demo',
            'user_id': self.user_employee.id,
            'department_id': self.rd_dept.id,
        })
        self.hr_leave_type = self.env['hr.leave.type'].with_user(self.user_hrmanager).create({
            'name': 'Time Off Type',
            'requires_allocation': 'no',
        })
        self.holiday = self.env['hr.leave'].with_context(mail_create_nolog=True, mail_notrack=True).with_user(self.user_employee).create({
            'name': 'Time Off Employee',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.hr_leave_type.id,
            'request_date_from': datetime(2020, 1, 15),
            'request_date_to': datetime(2020, 1, 15),
        })
        self.holiday.with_user(self.user_hrmanager).action_validate()

        # Ensure the event exists in the calendar and is correctly linked to the time off
        search_domain = [
            ('name', 'like', self.holiday.employee_id.name),
            ('start_date', '>=', self.holiday.request_date_from),
            ('stop_date', '<=', self.holiday.request_date_to),
        ]
        record = self.env['calendar.event'].search(search_domain)
        self.assertTrue(record, "The time off event should exist.")
        self.assertEqual(record.name, "Marc Demo on Time Off : 1 days",
                        "The event name should match the employee's time off description.")
        self.assertEqual(record.start_date, datetime(2020, 1, 15).date(),
                        "The start date should match the time off request.")
        self.assertEqual(record.stop_date, datetime(2020, 1, 15).date(),
                        "The end date should match the time off request.")

        # Mock Microsoft API response for event creation
        event_id = "123"
        event_iCalUId = "456"
        mock_insert.return_value = (event_id, event_iCalUId)
        mock_get_events.return_value = ([], None)

        # Sync calendar with Microsoft
        self.user_employee.with_user(self.user_employee).sudo()._sync_microsoft_calendar()
        self.call_post_commit_hooks()
        record.invalidate_recordset()
        mock_insert.assert_called_once()

        self.assertEqual(record.microsoft_id, event_id, "The Microsoft ID should be assigned correctly.")
        self.assertEqual(record.ms_universal_event_id, event_iCalUId, "The iCalUID should be assigned correctly.")
        self.assertEqual(record.need_sync_m, False, "The event should no longer need synchronization.")
        self.assertEqual(mock_insert.call_args[0][0].get('isOnlineMeeting'), False,
                        "Time off events should not be marked as an online meeting.")
        self.assertFalse(mock_insert.call_args[0][0].get('onlineMeetingProvider', False))

    @patch.object(MicrosoftCalendarService, 'insert')
    def test_skip_sync_for_non_synchronized_users_new_events(self, mock_insert):
        """
        Skip the synchro of new events by attendees when the organizer is not synchronized with Outlook.
        Otherwise, the event ownership will be lost to the attendee and it could generate duplicates in
        Odoo, as well cause problems in the future the synchronization of that event for the original owner.
        """
        with self.mock_datetime_and_now('2021-09-20 10:00:00'):
            # Ensure that the calendar synchronization of the attendee is active. Deactivate organizer's synchronization.
            self.attendee_user.microsoft_calendar_token_validity = datetime.now() + timedelta(minutes=60)
            self.assertTrue(self.env['calendar.event'].with_user(self.attendee_user)._check_microsoft_sync_status())
            self.organizer_user.microsoft_synchronization_stopped = True

            # Create an event with the organizer not synchronized and invite the synchronized attendee.
            self.simple_event_values['user_id'] = self.organizer_user.id
            self.simple_event_values['partner_ids'] = [Command.set([self.organizer_user.partner_id.id, self.attendee_user.partner_id.id])]
            event = self.env['calendar.event'].with_user(self.organizer_user).create(self.simple_event_values)
            self.assertTrue(event, "The event for the not synchronized owner must be created in Odoo.")

            # Synchronize the attendee's calendar, then make sure insert was not called.
            event.with_user(self.attendee_user).sudo()._sync_odoo2microsoft()
            mock_insert.assert_not_called()

            # Prepare mock return for the insertion.
            event_id = "123"
            event_iCalUId = "456"
            mock_insert.return_value = (event_id, event_iCalUId)

            # Activate the synchronization of the organizer and ensure that the event is now inserted.
            self.organizer_user.microsoft_synchronization_stopped = False
            self.organizer_user.microsoft_calendar_token_validity = datetime.now() + timedelta(minutes=60)
            self.organizer_user.with_user(self.organizer_user).restart_microsoft_synchronization()
            event.with_user(self.organizer_user).sudo()._sync_odoo2microsoft()
            self.call_post_commit_hooks()
            mock_insert.assert_called()

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_duplicate_event_microsoft_calendar(self, mock_insert, mock_get_events):
        """
        Test syncing an event from Odoo to Microsoft Calendar.
        """
        record = self.env["calendar.event"].with_user(self.organizer_user).create(self.simple_event_values)

        # Mock values to simulate Microsoft event creation
        event_id = "123"
        event_iCalUId = "456"
        mock_insert.return_value = (event_id, event_iCalUId)
        record2 = record.copy()
        # Prepare the mock event response from Microsoft
        self.response_from_outlook_organizer = {
            **self.simple_event_from_outlook_organizer,
            '_odoo_id': record.id,
        }
        self.response_from_outlook_organizer_1 = {
            **self.simple_event_from_outlook_organizer,
            '_odoo_id': record2.id,
        }
        mock_get_events.return_value = (MicrosoftEvent([self.response_from_outlook_organizer, self.response_from_outlook_organizer_1]), None)
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()
        self.call_post_commit_hooks()
        record.invalidate_recordset()
        record2.invalidate_recordset()

        # Check that Microsoft insert was called exactly once
        mock_insert.assert_called()

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_new_db_skip_odoo2microsoft_sync_previously_created_events(self, mock_insert, mock_get_events):
        """
        Skip the synchronization of previously created events if the database never synchronized with
        Outlook Calendar before. This is necessary for avoiding spamming lots of invitations in the first
        synchronization of users. A single ICP parameter 'first_synchronization_date' is shared in the DB
        to save down the first synchronization date of any of all users.
        """
        # During preparation: ensure that no user ever synchronized with Outlook Calendar
        # and create a local event waiting to be synchronized (need_sync_m: True).
        with self.mock_datetime_and_now('2024-01-01 10:00:00'):
            any_calendar_synchronized = self.env['res.users'].sudo().search_count(
                domain=[('microsoft_calendar_sync_token', '!=', False)],
                limit=1
            )
            self.assertFalse(any_calendar_synchronized)
            self.organizer_user.microsoft_synchronization_stopped = True
            event = self.env['calendar.event'].with_user(self.organizer_user).create({
                'name': "Odoo Local Event",
                'start': datetime(2024, 1, 1, 11, 0),
                'stop': datetime(2024, 1, 1, 13, 0),
                'user_id': self.organizer_user.id,
                'partner_ids': [(4, self.organizer_user.partner_id.id)],
                'need_sync_m': True
            })

        # For simulating a real world scenario, save the first synchronization date
        # one day later after creating the event that won't be synchronized.
        self.organizer_user._set_ICP_first_synchronization_date(
            fields.Datetime.from_string('2024-01-02 10:00:00')
        )

        # Ten seconds later the ICP parameter saving, make the synchronization between Odoo
        # and Outlook and ensure that insert was not called, i.e. the event got skipped.
        with self.mock_datetime_and_now('2024-01-02 10:00:10'):
            # Mock the return of 0 events from Outlook to Odoo, then activate the user's sync.
            mock_get_events.return_value = ([], None)
            self.organizer_user.microsoft_synchronization_stopped = False
            self.organizer_user.microsoft_calendar_token_validity = datetime.now() + timedelta(minutes=60)
            self.assertTrue(self.env['calendar.event'].with_user(self.organizer_user)._check_microsoft_sync_status())

            # Synchronize the user's calendar and call post commit hooks for analyzing the API calls.
            self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()
            self.call_post_commit_hooks()
            event.invalidate_recordset()
            mock_insert.assert_not_called()

    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_old_db_odoo2microsoft_sync_previously_created_events(self, mock_insert, mock_get_events):
        """
        Ensure that existing databases that are already synchronized with Outlook Calendar at some point
        won't skip any events creation in Outlook side during the first synchronization of the users.
        This test is important to make sure the behavior won't be changed for existing production envs.
        """
        # During preparation: ensure that the organizer is not synchronized with Outlook and
        # create a local event waiting to be synchronized (need_sync_m: True) without API calls.
        with self.mock_datetime_and_now('2024-01-01 10:00:00'):
            self.organizer_user.microsoft_synchronization_stopped = True
            event = self.env['calendar.event'].with_user(self.organizer_user).create({
                'name': "Odoo Local Event",
                'start': datetime(2024, 1, 1, 11, 0),
                'stop': datetime(2024, 1, 1, 13, 0),
                'user_id': self.organizer_user.id,
                'partner_ids': [(4, self.organizer_user.partner_id.id)],
                'need_sync_m': True
            })

            # Assign a next sync token to ANY user to simulate a previous sync in the DB.
            self.attendee_user.microsoft_calendar_sync_token = 'OngoingToken'

            # Mock the return of 0 events from Outlook to Odoo, then activate the user's sync.
            mock_get_events.return_value = ([], None)
            mock_insert.return_value = ('LocalEventSyncID', 'event_iCalUId')
            self.organizer_user.microsoft_synchronization_stopped = False
            self.organizer_user.microsoft_calendar_token_validity = datetime.now() + timedelta(minutes=60)
            self.assertTrue(self.env['calendar.event'].with_user(self.organizer_user)._check_microsoft_sync_status())

            # Synchronize the user's calendar and call post commit hooks for analyzing the API calls.
            # Our event must be synchronized normally in the first synchronization of the user.
            self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()
            self.call_post_commit_hooks()
            event.invalidate_recordset()
            mock_insert.assert_called_once()
            self.assertEqual(mock_insert.call_args[0][0]['subject'], event.name)

class TestSyncOdoo2MicrosoftMail(TestCommon, MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = []
        for n in range(1, 4):
            user = cls.env['res.users'].create({
                'name': f'user{n}',
                'login': f'user{n}',
                'email': f'user{n}@odoo.com',
                'microsoft_calendar_rtoken': f'abc{n}',
                'microsoft_calendar_token': f'abc{n}',
                'microsoft_calendar_token_validity': datetime(9999, 12, 31),
            })
            user.res_users_settings_id.write({
                'microsoft_synchronization_stopped': False,
                'microsoft_calendar_sync_token': f'{n}_sync_token',
            })
            cls.users += [user]

    @freeze_time("2020-01-01")
    @patch.object(User, '_get_microsoft_calendar_token', lambda user: user.microsoft_calendar_token)
    def test_event_creation_for_user(self):
        """Check that either emails or synchronization happens correctly when creating an event for another user."""
        user_root = self.env.ref('base.user_root')
        self.assertFalse(user_root.microsoft_calendar_token)
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        event_values = {
            'name': 'Event',
            'need_sync_m': True,
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
        }
        
        paused_sync_user = self.users[2]
        paused_sync_user.write({
            'email': 'ms.sync.paused@test.lan',
            'microsoft_synchronization_stopped': True,
            'name': 'Paused Microsoft Sync User',
            'login': 'ms_sync_paused_user',
        })
        self.assertTrue(paused_sync_user.microsoft_synchronization_stopped)

        for create_user, organizer, expect_mail, attendee in [
            (user_root, self.users[0], True, partner), # emulates online appointment with user 0
            (user_root, None, True, partner), # emulates online resource appointment
            (self.users[0], None, False, partner),
            (self.users[0], self.users[0], False, partner),
            (self.users[0], self.users[1], False, partner),
            # create user has paused sync and organizer can sync -> will not sync because of bug
            (paused_sync_user, self.users[0], True, paused_sync_user.partner_id),
        ]:
            with self.subTest(create_uid=create_user.name if create_user else None, user_id=organizer.name if organizer else None, attendee=attendee.name):
                with self.mock_mail_gateway(), patch.object(MicrosoftCalendarService, 'insert') as mock_insert:
                    mock_insert.return_value = ('1', '1')
                    self.env['calendar.event'].with_user(create_user).with_context(mail_notify_author=True).create({
                        **event_values,
                        'partner_ids': [(4, organizer.partner_id.id), (4, attendee.id)] if organizer else [(4, attendee.id)],
                        'user_id': organizer.id if organizer else False,
                    })
                    self.env.cr.postcommit.run()
                if not expect_mail:
                    self.assertNotSentEmail()
                    mock_insert.assert_called_once()
                    self.assert_dict_equal(mock_insert.call_args[0][0]['organizer'], {
                        'emailAddress': {'address': organizer.email if organizer else '', 'name': organizer.name if organizer else ''}
                    })
                elif expect_mail:
                    mock_insert.assert_not_called()
                    self.assertMailMail(attendee, 'sent', author=(organizer or create_user).partner_id)
