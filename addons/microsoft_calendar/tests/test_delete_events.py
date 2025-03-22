# -*- coding: utf-8 -*-
from unittest.mock import patch, ANY, call
from datetime import timedelta

from odoo import fields

from odoo.exceptions import UserError
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.models.res_users import User
from odoo.addons.microsoft_calendar.tests.common import (
    TestCommon,
    mock_get_token,
    _modified_date_in_the_future,
    patch_api
)

@patch.object(User, '_get_microsoft_calendar_token', mock_get_token)
class TestDeleteEvents(TestCommon):

    @patch_api
    def setUp(self):
        super(TestDeleteEvents, self).setUp()
        self.create_events_for_tests()

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_delete_simple_event_from_odoo_organizer_calendar(self, mock_delete):
        event_id = self.simple_event.ms_organizer_event_id

        self.simple_event.with_user(self.organizer_user).unlink()
        self.call_post_commit_hooks()
        self.simple_event.invalidate_recordset()

        self.assertFalse(self.simple_event.exists())
        mock_delete.assert_called_once_with(
            event_id,
            token=mock_get_token(self.organizer_user),
            timeout=ANY
        )

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_delete_simple_event_from_odoo_attendee_calendar(self, mock_delete):
        event_id = self.simple_event.ms_organizer_event_id

        self.simple_event.with_user(self.attendee_user).unlink()
        self.call_post_commit_hooks()
        self.simple_event.invalidate_recordset()

        self.assertFalse(self.simple_event.exists())
        mock_delete.assert_called_once_with(
            event_id,
            token=mock_get_token(self.organizer_user),
            timeout=ANY
        )

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_archive_simple_event_from_odoo_organizer_calendar(self, mock_delete):
        event_id = self.simple_event.ms_organizer_event_id

        self.simple_event.with_user(self.organizer_user).write({'active': False})
        self.call_post_commit_hooks()
        self.simple_event.invalidate_recordset()

        self.assertTrue(self.simple_event.exists())
        self.assertFalse(self.simple_event.active)
        mock_delete.assert_called_once_with(
            event_id,
            token=mock_get_token(self.organizer_user),
            timeout=ANY
        )

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_archive_simple_event_from_odoo_attendee_calendar(self, mock_delete):
        event_id = self.simple_event.ms_organizer_event_id

        self.simple_event.with_user(self.attendee_user).write({'active': False})
        self.call_post_commit_hooks()
        self.simple_event.invalidate_recordset()

        self.assertTrue(self.simple_event.exists())
        self.assertFalse(self.simple_event.active)
        mock_delete.assert_called_once_with(
            event_id,
            token=mock_get_token(self.organizer_user),
            timeout=ANY
        )

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_archive_several_events_at_once(self, mock_delete):
        """
        Archive several events at once should not produce any exception.
        """
        # arrange
        several_simple_events = self.several_events.filtered(lambda ev: not ev.recurrency and ev.microsoft_id)
        # act
        several_simple_events.action_archive()
        self.call_post_commit_hooks()
        several_simple_events.invalidate_recordset()

        # assert
        self.assertFalse(all(e.active for e in several_simple_events))

        mock_delete.assert_has_calls([
            call(e.ms_organizer_event_id, token=ANY, timeout=ANY)
            for e in several_simple_events
        ])

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_cancel_simple_event_from_outlook_organizer_calendar(self, mock_get_events):
        """
        In his Outlook calendar, the organizer cannot delete the event, he can only cancel it.
        """
        event_id = self.simple_event.ms_organizer_event_id
        mock_get_events.return_value = (
            MicrosoftEvent([{
                "id": event_id,
                "@removed": {"reason": "deleted"}
            }]),
            None
        )
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()
        self.assertFalse(self.simple_event.exists())

    def test_delete_simple_event_from_outlook_attendee_calendar(self):
        """
        If an attendee deletes an event from its Outlook calendar, during the sync, Odoo will be notified that
        this event has been deleted BUT only with the attendees's calendar event id and not with the global one
        (called iCalUId). That means, it's not possible to match this deleted event with an Odoo event.

        LIMITATION:

        Unfortunately, there is no magic solution:
            1) keep the list of calendar events ids linked to a unique iCalUId but all Odoo users may not have synced
            their Odoo calendar, leading to missing ids in the list => bad solution.
            2) call the microsoft API to get the iCalUId matching the received event id => as the event has already
            been deleted, this call may return an error.
        """

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_delete_one_event_from_recurrence_from_odoo_calendar(self, mock_delete):
        if not self.sync_odoo_recurrences_with_outlook_feature():
            return
        # arrange
        idx = 2
        event_id = self.recurrent_events[idx].ms_organizer_event_id

        # act
        self.recurrent_events[idx].with_user(self.organizer_user).unlink()
        self.call_post_commit_hooks()

        # assert
        self.assertFalse(self.recurrent_events[idx].exists())
        self.assertEqual(len(self.recurrence.calendar_event_ids), self.recurrent_events_count - 1)
        mock_delete.assert_called_once_with(
            event_id,
            token=mock_get_token(self.organizer_user),
            timeout=ANY
        )

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_delete_first_event_from_recurrence_from_odoo_calendar(self, mock_delete):
        if not self.sync_odoo_recurrences_with_outlook_feature():
            return
        # arrange
        idx = 0
        event_id = self.recurrent_events[idx].ms_organizer_event_id

        # act
        self.recurrent_events[idx].with_user(self.organizer_user).unlink()
        self.call_post_commit_hooks()

        # assert
        self.assertFalse(self.recurrent_events[idx].exists())
        self.assertEqual(len(self.recurrence.calendar_event_ids), self.recurrent_events_count - 1)
        self.assertEqual(self.recurrence.base_event_id, self.recurrent_events[1])
        mock_delete.assert_called_once_with(
            event_id,
            token=mock_get_token(self.organizer_user),
            timeout=ANY
        )

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_delete_one_event_from_recurrence_from_outlook_calendar(self, mock_get_events):
        """
        When a single event is removed from a recurrence, Outlook returns the recurrence and
        events which still exist.
        """
        # arrange
        idx = 3
        rec_values = [
            dict(
                event,
                lastModifiedDateTime=_modified_date_in_the_future(self.recurrence)
            )
            for i, event in enumerate(self.recurrent_event_from_outlook_organizer)
            if i != (idx + 1)  # + 1 because recurrent_event_from_outlook_organizer contains the recurrence itself as first item
        ]
        event_to_remove = self.recurrent_events[idx]
        mock_get_events.return_value = (MicrosoftEvent(rec_values), None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        self.assertFalse(event_to_remove.exists())
        self.assertEqual(len(self.recurrence.calendar_event_ids), self.recurrent_events_count - 1)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_delete_first_event_from_recurrence_from_outlook_calendar(self, mock_get_events):
        # arrange
        rec_values = [
            dict(
                event,
                lastModifiedDateTime=_modified_date_in_the_future(self.recurrence)
            )
            for i, event in enumerate(self.recurrent_event_from_outlook_organizer)
            if i != 1
        ]
        event_to_remove = self.recurrent_events[0]
        next_base_event = self.recurrent_events[1]
        mock_get_events.return_value = (MicrosoftEvent(rec_values), None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        self.assertFalse(event_to_remove.exists())
        self.assertEqual(len(self.recurrence.calendar_event_ids), self.recurrent_events_count - 1)
        self.assertEqual(self.recurrence.base_event_id, next_base_event)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_delete_one_event_and_future_from_recurrence_from_outlook_calendar(self, mock_get_events):
        if not self.sync_odoo_recurrences_with_outlook_feature():
            return
        # arrange
        idx = range(4, self.recurrent_events_count)
        rec_values = [
            dict(
                event,
                lastModifiedDateTime=_modified_date_in_the_future(self.recurrence)
            )
            for i, event in enumerate(self.recurrent_event_from_outlook_organizer)
            if i not in [x + 1 for x in idx]
        ]
        event_to_remove = [e for i, e in enumerate(self.recurrent_events) if i in idx]
        mock_get_events.return_value = (MicrosoftEvent(rec_values), None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        for e in event_to_remove:
            self.assertFalse(e.exists())
        self.assertEqual(len(self.recurrence.calendar_event_ids), self.recurrent_events_count - len(idx))

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_delete_first_event_and_future_from_recurrence_from_outlook_calendar(self, mock_get_events):
        """
        In Outlook, deleting the first event and future ones is the same than removing all the recurrence.
        """
        # arrange
        mock_get_events.return_value = (
            MicrosoftEvent([{
                "id": self.recurrence.ms_organizer_event_id,
                "@removed": {"reason": "deleted"}
            }]),
            None
        )

        # act
        self.organizer_user.with_context(dont_notify=True).with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        self.assertFalse(self.recurrence.exists())
        self.assertFalse(self.recurrence.calendar_event_ids.exists())

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_delete_all_events_from_recurrence_from_outlook_calendar(self, mock_get_events):
        """
        Same than test_delete_first_event_and_future_from_recurrence_from_outlook_calendar.
        """

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_delete_single_event_from_recurrence_from_odoo_calendar(self, mock_delete):
        """
        Deletes the base_event of a recurrence and checks if the event was archived and the recurrence was updated.
        """
        if not self.sync_odoo_recurrences_with_outlook_feature():
            return
        # arrange
        idx = 0
        event_id = self.recurrent_events[idx].ms_organizer_event_id

        # act
        self.recurrent_events[idx].with_user(self.organizer_user).action_mass_archive('self_only')
        self.call_post_commit_hooks()

        # assert that event is not active anymore and that a new base_event was select for the recurrence
        self.assertFalse(self.recurrent_events[idx].active)
        self.assertNotEqual(self.id, self.recurrent_events[idx].recurrence_id.base_event_id.id)
        self.assertTrue(self.id not in [rec.id for rec in self.recurrent_events[idx].recurrence_id.calendar_event_ids])
        mock_delete.assert_called_once_with(
            event_id,
            token=mock_get_token(self.organizer_user),
            timeout=ANY
        )

    @patch.object(MicrosoftCalendarService, 'delete')
    def test_delete_recurrence_previously_synced(self, mock_delete):
        # Arrange: select recurrent event and update token validity to simulate an active sync environment.
        idx = 0
        self.organizer_user.microsoft_calendar_token_validity = fields.Datetime.now() + timedelta(hours=1)

        # Act: try to delete a recurrent event that was already synced.
        with self.assertRaises(UserError):
            self.recurrent_events[idx].with_user(self.organizer_user).action_mass_archive('all_events')
            self.call_post_commit_hooks()

        # Ensure that event remains undeleted after deletion attempt and delete method wasn't called.
        self.assertTrue(self.recurrent_events[idx].with_user(self.organizer_user)._check_microsoft_sync_status())
        self.assertTrue(self.recurrent_events[idx].active)
        mock_delete.assert_not_called()

    def test_forbid_recurrence_unlinking_list_view(self):
        # Forbid recurrence unlinking from list view with sync on.
        self.assertTrue(self.env['calendar.event'].with_user(self.organizer_user)._check_microsoft_sync_status())
        with self.assertRaises(UserError):
            self.recurrent_events.unlink()

        # Allow recurrence unlinking when update comes from Microsoft (dont_notify=True).
        self.recurrent_events[2:].with_context(dont_notify=True).unlink()
        self.assertTrue(all(not event.exists() for event in self.recurrent_events[2:]), "Recurrent event must be deleted after unlink from Microsoft.")

        # Allow unlinking recurrence when sync is off for the current user.
        self.organizer_user.microsoft_synchronization_stopped = True
        self.assertFalse(self.env['calendar.event'].with_user(self.organizer_user)._check_microsoft_sync_status())
        self.recurrent_events[1].with_user(self.organizer_user).unlink()
        self.assertFalse(self.recurrent_events[1].exists(), "Recurrent event must be deleted after unlink with sync off.")
