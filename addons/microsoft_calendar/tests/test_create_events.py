from unittest.mock import patch

from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.models.res_users import User
from odoo.addons.microsoft_calendar.tests.common import TestCommon, mock_get_token
from odoo.exceptions import ValidationError

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
    def test_create_simple_event_from_outlook_attendee_calendar_and_organizer_does_not_exist_in_odoo(
        self, mock_get_events
    ):
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

    @patch.object(MicrosoftCalendarService, 'insert')
    def test_create_recurrent_event_without_sync(self, mock_insert):
        """
        A Odoo recurrent event is created when Outlook sync is not enabled.
        """

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
        self.assertEqual(recurrence.ms_organizer_event_id, event_id)
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

        self.assertEqual(recurrence.ms_organizer_event_id, False)
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
