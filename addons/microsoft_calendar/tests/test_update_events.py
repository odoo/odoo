# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.parser import parse
import logging
import pytz
from unittest.mock import patch, ANY

from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.models.res_users import User
from odoo.addons.microsoft_calendar.utils.event_id_storage import combine_ids
from odoo.addons.microsoft_calendar.tests.common import TestCommon, mock_get_token, _modified_date_in_the_future, patch_api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

@patch.object(User, '_get_microsoft_calendar_token', mock_get_token)
class TestUpdateEvents(TestCommon):

    @patch_api
    def setUp(self):
        super(TestUpdateEvents, self).setUp()
        self.create_events_for_tests()

    # -------------------------------------------------------------------------------
    # Update from Odoo to Outlook
    # -------------------------------------------------------------------------------

    # ------ Simple event ------

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_odoo_simple_event_without_sync(self, mock_patch):
        """
        Update an Odoo event without Outlook sync enabled
        """

        # arrange
        self.organizer_user.microsoft_synchronization_stopped = True
        self.simple_event.need_sync_m = False

        # act
        self.simple_event.write({"name": "my new simple event"})
        self.call_post_commit_hooks()
        self.simple_event.invalidate_cache()

        # assert
        mock_patch.assert_not_called()
        self.assertEqual(self.simple_event.need_sync_m, False)

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_simple_event_from_odoo(self, mock_patch):
        """
        Update an Odoo event with Outlook sync enabled
        """

        # arrange
        mock_patch.return_value = True

        # act
        res = self.simple_event.with_user(self.organizer_user).write({"name": "my new simple event"})
        self.call_post_commit_hooks()
        self.simple_event.invalidate_cache()

        # assert
        self.assertTrue(res)
        mock_patch.assert_called_once_with(
            self.simple_event.ms_organizer_event_id,
            {"subject": "my new simple event"},
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )
        self.assertEqual(self.simple_event.name, "my new simple event")

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_simple_event_from_odoo_attendee_calendar(self, mock_patch):
        """
        Update an Odoo event from the attendee calendar.
        """

        # arrange
        mock_patch.return_value = True

        # act
        res = self.simple_event.with_user(self.attendee_user).write({"name": "my new simple event"})
        self.call_post_commit_hooks()
        self.simple_event.invalidate_cache()

        # assert
        self.assertTrue(res)
        mock_patch.assert_called_once_with(
            self.simple_event.ms_organizer_event_id,
            {"subject": "my new simple event"},
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )
        self.assertEqual(self.simple_event.name, "my new simple event")

    # ------ One event in a recurrence ------

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_name_of_one_event_of_recurrence_from_odoo(self, mock_patch):
        """
        Update one Odoo event name from a recurrence from the organizer calendar.
        """

        # arrange
        new_name = "my specific event in recurrence"
        modified_event_id = 4

        # act
        res = self.recurrent_events[modified_event_id].with_user(self.organizer_user).write({
            "recurrence_update": "self_only",
            "name": new_name,
        })
        self.call_post_commit_hooks()
        self.recurrent_events[modified_event_id].invalidate_cache()

        # assert
        self.assertTrue(res)
        mock_patch.assert_called_once_with(
            self.recurrent_events[modified_event_id].ms_organizer_event_id,
            {'seriesMasterId': 'REC123', 'type': 'exception', "subject": new_name},
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )
        self.assertEqual(self.recurrent_events[modified_event_id].name, new_name)
        self.assertEqual(self.recurrent_events[modified_event_id].follow_recurrence, True)

        for i in range(self.recurrent_events_count):
            if i != modified_event_id:
                self.assertNotEqual(self.recurrent_events[i].name, new_name)

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_start_of_one_event_of_recurrence_from_odoo(self, mock_patch):
        """
        Update one Odoo event start date from a recurrence from the organizer calendar.
        """

        # arrange
        new_date = datetime(2021, 9, 29, 10, 0, 0)
        modified_event_id = 4

        # act
        res = self.recurrent_events[modified_event_id].with_user(self.organizer_user).write({
            "recurrence_update": "self_only",
            "start": new_date.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.call_post_commit_hooks()
        self.recurrent_events[modified_event_id].invalidate_cache()

        # assert
        self.assertTrue(res)
        mock_patch.assert_called_once_with(
            self.recurrent_events[modified_event_id].ms_organizer_event_id,
            {
                'seriesMasterId': 'REC123',
                'type': 'exception',
                'start': {
                    'dateTime': pytz.utc.localize(new_date).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'end': {
                    'dateTime': pytz.utc.localize(new_date + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'isAllDay': False
            },
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )
        self.assertEqual(self.recurrent_events[modified_event_id].start, new_date)
        self.assertEqual(self.recurrent_events[modified_event_id].follow_recurrence, False)

        for i in range(self.recurrent_events_count):
            if i != modified_event_id:
                self.assertNotEqual(self.recurrent_events[i].start, new_date)
                self.assertEqual(self.recurrent_events[i].follow_recurrence, True)

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_start_of_one_event_of_recurrence_from_odoo_with_overlap(self, mock_patch):
        """
        Update one Odoo event start date from a recurrence from the organizer calendar, in order to
        overlap another existing event.
        """
        # arrange
        new_date = datetime(2021, 9, 27, 10, 0, 0)
        modified_event_id = 4

        # act
        with self.assertRaises(UserError):
            self.recurrent_events[modified_event_id].with_user(self.organizer_user).write({
                "recurrence_update": "self_only",
                "start": new_date.strftime("%Y-%m-%d %H:%M:%S"),
            })
            self.call_post_commit_hooks()
            self.recurrent_events.invalidate_cache()

        # assert
        mock_patch.assert_not_called()

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_name_of_one_event_of_recurrence_from_odoo_attendee_calendar(self, mock_patch):
        """
        Update one Odoo event name from a recurrence from the atendee calendar.
        """

        # arrange
        new_name = "my specific event in recurrence"
        modified_event_id = 4

        # act
        res = self.recurrent_events[modified_event_id].with_user(self.attendee_user).write({
            "recurrence_update": "self_only",
            "name": new_name
        })
        self.call_post_commit_hooks()
        self.recurrent_events[modified_event_id].invalidate_cache()

        # assert
        self.assertTrue(res)
        mock_patch.assert_called_once_with(
            self.recurrent_events[modified_event_id].ms_organizer_event_id,
            {'seriesMasterId': 'REC123', 'type': 'exception', "subject": new_name},
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )
        self.assertEqual(self.recurrent_events[modified_event_id].name, new_name)
        self.assertEqual(self.recurrent_events[modified_event_id].follow_recurrence, True)

    # ------ One and future events in a recurrence ------

    @patch.object(MicrosoftCalendarService, 'delete')
    @patch.object(MicrosoftCalendarService, 'insert')
    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_name_of_one_and_future_events_of_recurrence_from_odoo(
        self, mock_patch, mock_insert, mock_delete
    ):
        """
        Update a Odoo event name and future events from a recurrence from the organizer calendar.
        """

        # arrange
        new_name = "my specific event in recurrence"
        modified_event_id = 4

        # act
        res = self.recurrent_events[modified_event_id].with_user(self.organizer_user).write({
            "recurrence_update": "future_events",
            "name": new_name,
        })
        self.call_post_commit_hooks()
        self.recurrent_events.invalidate_cache()

        # assert
        self.assertTrue(res)
        self.assertEqual(mock_patch.call_count, self.recurrent_events_count - modified_event_id)
        for i in range(modified_event_id, self.recurrent_events_count):
            mock_patch.assert_any_call(
                self.recurrent_events[i].ms_organizer_event_id,
                {'seriesMasterId': 'REC123', 'type': 'exception', "subject": new_name},
                token=mock_get_token(self.organizer_user),
                timeout=ANY,
            )
        for i in range(modified_event_id, self.recurrent_events_count):
            self.assertEqual(self.recurrent_events[i].name, new_name)
            self.assertEqual(self.recurrent_events[i].follow_recurrence, True)

        for i in range(modified_event_id):
            self.assertNotEqual(self.recurrent_events[i].name, new_name)

    @patch.object(MicrosoftCalendarService, 'delete')
    @patch.object(MicrosoftCalendarService, 'insert')
    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_start_of_one_and_future_events_of_recurrence_from_odoo(
        self, mock_patch, mock_insert, mock_delete
    ):
        """
        Update a Odoo event start date and future events from a recurrence from the organizer calendar.
        """

        # When a time-related field is changed, the event does not follow the recurrence scheme anymore.
        # With Outlook, another constraint is that the new start of the event cannot overlap/cross the start
        # date of another event of the recurrence (see microsoft_calendar/models/calendar.py
        # _check_recurrence_overlapping() for more explanation)
        #
        # In this case, as we also update future events, the recurrence should be splitted into 2 parts:
        #  - the original recurrence should end just before the first updated event
        #  - a second recurrence should start at the first updated event

        # arrange
        new_date = datetime(2021, 9, 29, 10, 0, 0)
        modified_event_id = 4
        existing_recurrences = self.env["calendar.recurrence"].search([])

        expected_deleted_event_ids = [
            r.ms_organizer_event_id
            for i, r in enumerate(self.recurrent_events)
            if i in range(modified_event_id + 1, self.recurrent_events_count)
        ]

        # act
        res = self.recurrent_events[modified_event_id].with_user(self.organizer_user).write({
            "recurrence_update": "future_events",
            "start": new_date.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.call_post_commit_hooks()
        self.recurrent_events.invalidate_cache()

        # assert
        new_recurrences = self.env["calendar.recurrence"].search([]) - existing_recurrences

        self.assertTrue(res)

        # a new recurrence should be created from the modified event to the end
        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(new_recurrences.base_event_id.start, new_date)
        self.assertEqual(len(new_recurrences.calendar_event_ids), self.recurrent_events_count - modified_event_id)

        # future events of the old recurrence should have been removed
        for e_id in expected_deleted_event_ids:
            mock_delete.assert_any_call(
                e_id,
                token=mock_get_token(self.organizer_user),
                timeout=ANY,
            )

        # the base event should have been modified
        mock_patch.assert_called_once_with(
            self.recurrent_events[modified_event_id].ms_organizer_event_id,
            {
                'seriesMasterId': 'REC123',
                'type': 'exception',
                'start': {
                    'dateTime': pytz.utc.localize(new_date).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'end': {
                    'dateTime': pytz.utc.localize(new_date + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'isAllDay': False
            },
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )

    @patch.object(MicrosoftCalendarService, 'delete')
    @patch.object(MicrosoftCalendarService, 'insert')
    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_start_of_one_and_future_events_of_recurrence_from_odoo_with_overlap(
        self, mock_patch, mock_insert, mock_delete
    ):
        """
        Update a Odoo event start date and future events from a recurrence from the organizer calendar,
        overlapping an existing event.
        """

        # arrange
        new_date = datetime(2021, 9, 27, 10, 0, 0)
        modified_event_id = 4
        existing_recurrences = self.env["calendar.recurrence"].search([])

        expected_deleted_event_ids = [
            r.ms_organizer_event_id
            for i, r in enumerate(self.recurrent_events)
            if i in range(modified_event_id + 1, self.recurrent_events_count)
        ]

        # as the test overlap the previous event of the updated event, this previous event
        # should be removed too
        expected_deleted_event_ids += [self.recurrent_events[modified_event_id - 1].ms_organizer_event_id]

        # act
        res = self.recurrent_events[modified_event_id].with_user(self.organizer_user).write({
            "recurrence_update": "future_events",
            "start": new_date.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.call_post_commit_hooks()
        self.recurrent_events.invalidate_cache()

        # assert
        new_recurrences = self.env["calendar.recurrence"].search([]) - existing_recurrences

        self.assertTrue(res)

        # a new recurrence should be created from the modified event to the end
        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(new_recurrences.base_event_id.start, new_date)
        self.assertEqual(len(new_recurrences.calendar_event_ids), self.recurrent_events_count - modified_event_id + 1)

        # future events of the old recurrence should have been removed + the overlapped event
        for e_id in expected_deleted_event_ids:
            mock_delete.assert_any_call(
                e_id,
                token=mock_get_token(self.organizer_user),
                timeout=ANY,
            )

        # the base event should have been modified
        mock_patch.assert_called_once_with(
            self.recurrent_events[modified_event_id].ms_organizer_event_id,
            {
                'seriesMasterId': 'REC123',
                'type': 'exception',
                'start': {
                    'dateTime': pytz.utc.localize(new_date).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'end': {
                    'dateTime': pytz.utc.localize(new_date + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'isAllDay': False
            },
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )

    @patch.object(MicrosoftCalendarService, 'delete')
    @patch.object(MicrosoftCalendarService, 'insert')
    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_one_and_future_events_of_recurrence_from_odoo_attendee_calendar(
        self, mock_patch, mock_insert, mock_delete
    ):
        """
        Update a Odoo event name and future events from a recurrence from the attendee calendar.
        """

        # arrange
        new_date = datetime(2021, 9, 29, 10, 0, 0)
        modified_event_id = 4
        existing_recurrences = self.env["calendar.recurrence"].search([])

        expected_deleted_event_ids = [
            r.ms_organizer_event_id
            for i, r in enumerate(self.recurrent_events)
            if i in range(modified_event_id + 1, self.recurrent_events_count)
        ]

        # act
        res = self.recurrent_events[modified_event_id].with_user(self.attendee_user).write({
            "recurrence_update": "future_events",
            "start": new_date.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.call_post_commit_hooks()
        self.recurrent_events.invalidate_cache()

        # assert
        new_recurrences = self.env["calendar.recurrence"].search([]) - existing_recurrences

        self.assertTrue(res)

        # a new recurrence should be created from the modified event to the end
        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(new_recurrences.base_event_id.start, new_date)
        self.assertEqual(len(new_recurrences.calendar_event_ids), self.recurrent_events_count - modified_event_id)

        # future events of the old recurrence should have been removed
        for e_id in expected_deleted_event_ids:
            mock_delete.assert_any_call(
                e_id,
                token=mock_get_token(self.organizer_user),
                timeout=ANY,
            )

        # the base event should have been modified
        mock_patch.assert_called_once_with(
            self.recurrent_events[modified_event_id].ms_organizer_event_id,
            {
                'seriesMasterId': 'REC123',
                'type': 'exception',
                'start': {
                    'dateTime': pytz.utc.localize(new_date).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'end': {
                    'dateTime': pytz.utc.localize(new_date + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'isAllDay': False
            },
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )

    # ------ All events in a recurrence ------

    @patch.object(MicrosoftCalendarService, 'delete')
    @patch.object(MicrosoftCalendarService, 'insert')
    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_name_of_all_events_of_recurrence_from_odoo(
        self, mock_patch, mock_insert, mock_delete
    ):
        """
        Update all events name from a recurrence from the organizer calendar.
        """

        # arrange
        new_name = "my specific event in recurrence"

        # act
        res = self.recurrent_events[0].with_user(self.organizer_user).write({
            "recurrence_update": "all_events",
            "name": new_name,
        })
        self.call_post_commit_hooks()
        self.recurrent_events.invalidate_cache()

        # assert
        self.assertTrue(res)
        self.assertEqual(mock_patch.call_count, self.recurrent_events_count)
        for i in range(self.recurrent_events_count):
            mock_patch.assert_any_call(
                self.recurrent_events[i].ms_organizer_event_id,
                {'seriesMasterId': 'REC123', 'type': 'exception', "subject": new_name},
                token=mock_get_token(self.organizer_user),
                timeout=ANY,
            )
            self.assertEqual(self.recurrent_events[i].name, new_name)
            self.assertEqual(self.recurrent_events[i].follow_recurrence, True)

    @patch.object(MicrosoftCalendarService, 'delete')
    @patch.object(MicrosoftCalendarService, 'insert')
    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_start_of_all_events_of_recurrence_from_odoo(
        self, mock_patch, mock_insert, mock_delete
    ):
        """
        Update all events start date from a recurrence from the organizer calendar.
        """

        # arrange
        new_date = datetime(2021, 9, 25, 10, 0, 0)
        existing_recurrences = self.env["calendar.recurrence"].search([])
        expected_deleted_event_ids = [
            r.ms_organizer_event_id
            for i, r in enumerate(self.recurrent_events)
            if i in range(1, self.recurrent_events_count)
        ]

        # act
        res = self.recurrent_events[0].with_user(self.organizer_user).write({
            "recurrence_update": "all_events",
            "start": new_date.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.call_post_commit_hooks()
        self.recurrent_events.invalidate_cache()

        # assert
        new_recurrences = self.env["calendar.recurrence"].search([]) - existing_recurrences

        self.assertTrue(res)

        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(new_recurrences.base_event_id.start, new_date)
        self.assertEqual(len(new_recurrences.calendar_event_ids), self.recurrent_events_count)

        mock_patch.assert_called_once_with(
            self.recurrent_events[0].ms_organizer_event_id,
            {
                'seriesMasterId': 'REC123',
                'type': 'exception',
                'start': {
                    'dateTime': pytz.utc.localize(new_date).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'end': {
                    'dateTime': pytz.utc.localize(new_date + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'isAllDay': False
            },
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )

        # events (except the base one) of the old recurrence should have been removed
        for e_id in expected_deleted_event_ids:
            mock_delete.assert_any_call(
                e_id,
                token=mock_get_token(self.organizer_user),
                timeout=ANY,
            )

    @patch.object(MicrosoftCalendarService, 'delete')
    @patch.object(MicrosoftCalendarService, 'insert')
    @patch.object(MicrosoftCalendarService, 'patch')
    def test_update_all_events_of_recurrence_from_odoo_attendee_calendar(
        self, mock_patch, mock_insert, mock_delete
    ):
        """
        Update all events start date from a recurrence from the attendee calendar.
        """

        # arrange
        new_date = datetime(2021, 9, 25, 10, 0, 0)
        existing_recurrences = self.env["calendar.recurrence"].search([])
        expected_deleted_event_ids = [
            r.ms_organizer_event_id
            for i, r in enumerate(self.recurrent_events)
            if i in range(1, self.recurrent_events_count)
        ]

        # act
        res = self.recurrent_events[0].with_user(self.attendee_user).write({
            "recurrence_update": "all_events",
            "start": new_date.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self.call_post_commit_hooks()
        self.recurrent_events.invalidate_cache()

        # assert
        new_recurrences = self.env["calendar.recurrence"].search([]) - existing_recurrences

        self.assertTrue(res)

        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(new_recurrences.base_event_id.start, new_date)
        self.assertEqual(len(new_recurrences.calendar_event_ids), self.recurrent_events_count)

        mock_patch.assert_called_once_with(
            self.recurrent_events[0].ms_organizer_event_id,
            {
                'seriesMasterId': 'REC123',
                'type': 'exception',
                'start': {
                    'dateTime': pytz.utc.localize(new_date).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'end': {
                    'dateTime': pytz.utc.localize(new_date + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Europe/London'
                },
                'isAllDay': False
            },
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )

        # events (except the base one) of the old recurrence should have been removed
        for e_id in expected_deleted_event_ids:
            mock_delete.assert_any_call(
                e_id,
                token=mock_get_token(self.organizer_user),
                timeout=ANY,
            )

    # -------------------------------------------------------------------------------
    # Update from Outlook to Odoo
    # -------------------------------------------------------------------------------

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_simple_event_from_outlook_organizer_calendar(self, mock_get_events):
        """
        Update a simple event from Outlook organizer calendar.
        """

        # arrange
        new_name = "update simple event"
        mock_get_events.return_value = (
            MicrosoftEvent([dict(
                self.simple_event_from_outlook_organizer,
                subject=new_name,
                type="exception",
                lastModifiedDateTime=_modified_date_in_the_future(self.simple_event)
            )]), None
        )

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        self.assertEqual(self.simple_event.name, new_name)
        self.assertEqual(self.simple_event.follow_recurrence, False)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_simple_event_from_outlook_attendee_calendar(self, mock_get_events):
        """
        Update a simple event from Outlook attendee calendar.
        """

        # arrange
        new_name = "update simple event"
        mock_get_events.return_value = (
            MicrosoftEvent([dict(
                dict(self.simple_event_from_outlook_organizer, id=789),  # same iCalUId but different id
                subject=new_name,
                type="exception",
                lastModifiedDateTime=_modified_date_in_the_future(self.simple_event)
            )]), None
        )

        # act
        self.attendee_user.with_user(self.attendee_user).sudo()._sync_microsoft_calendar()

        # assert
        self.assertEqual(self.simple_event.name, new_name)
        self.assertEqual(self.simple_event.follow_recurrence, False)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_name_of_one_event_of_recurrence_from_outlook_organizer_calendar(self, mock_get_events):
        """
        Update one event name from a recurrence from Outlook organizer calendar.
        """

        # arrange
        new_name = "another event name"
        from_event_index = 2
        events = self.recurrent_event_from_outlook_organizer
        events[from_event_index] = dict(
            events[from_event_index],
            subject=new_name,
            type="exception",
            lastModifiedDateTime=_modified_date_in_the_future(self.simple_event)
        )
        ms_event_id = events[from_event_index]['id']
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        updated_event = self.env["calendar.event"].search([('ms_organizer_event_id', '=', ms_event_id)])
        self.assertEqual(updated_event.name, new_name)
        self.assertEqual(updated_event.follow_recurrence, False)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_start_of_one_event_of_recurrence_from_outlook_organizer_calendar(self, mock_get_events):
        """
        Update one event start date from a recurrence from Outlook organizer calendar.
        """

        # arrange
        new_date = datetime(2021, 9, 25, 10, 0, 0)
        from_event_index = 3
        events = self.recurrent_event_from_outlook_organizer
        events[from_event_index] = dict(
            events[from_event_index],
            start={'dateTime': new_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"), 'timeZone': 'UTC'},
            type="exception",
            lastModifiedDateTime=_modified_date_in_the_future(self.recurrent_base_event)
        )
        ms_event_id = events[from_event_index]['id']
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        updated_event = self.env["calendar.event"].search([('ms_organizer_event_id', '=', ms_event_id)])
        self.assertEqual(updated_event.start, new_date)
        self.assertEqual(updated_event.follow_recurrence, False)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_start_of_one_event_of_recurrence_from_outlook_organizer_calendar_with_overlap(
        self, mock_get_events
    ):
        """
        Update one event start date from a recurrence from Outlook organizer calendar, with event overlap.
        """

        # arrange
        new_date = datetime(2021, 9, 23, 10, 0, 0)
        from_event_index = 3
        events = self.recurrent_event_from_outlook_organizer
        events[from_event_index] = dict(
            events[from_event_index],
            start={'dateTime': new_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"), 'timeZone': 'UTC'},
            type="exception",
            lastModifiedDateTime=_modified_date_in_the_future(self.recurrent_base_event)
        )
        ms_event_id = events[from_event_index]['id']
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        updated_event = self.env["calendar.event"].search([('ms_organizer_event_id', '=', ms_event_id)])
        self.assertEqual(updated_event.start, new_date)
        self.assertEqual(updated_event.follow_recurrence, False)

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_name_of_one_event_and_future_of_recurrence_from_outlook_organizer_calendar(self, mock_get_events):
        """
        Update one event name and future events from a recurrence from Outlook organizer calendar.
        """

        # arrange
        new_name = "another event name"
        from_event_index = 3
        events = self.recurrent_event_from_outlook_organizer
        for i in range(from_event_index, len(events)):
            events[i] = dict(
                events[i],
                subject=f"{new_name}_{i}",
                type="exception",
                lastModifiedDateTime=_modified_date_in_the_future(self.recurrent_base_event)
            )
        ms_event_ids = {
            events[i]['id']: events[i]['subject'] for i in range(from_event_index, len(events))
        }
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        updated_events = self.env["calendar.event"].search([
            ('ms_organizer_event_id', 'in', tuple(ms_event_ids.keys()))
        ])
        for e in updated_events:
            self.assertEqual(e.name, ms_event_ids[e.ms_organizer_event_id])

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_start_of_one_event_and_future_of_recurrence_from_outlook_organizer_calendar(self, mock_get_events):
        """
        Update one event start date and future events from a recurrence from Outlook organizer calendar.

        When a time field is modified on an event and the future events of the recurrence, the recurrence is splitted:
        - the first one is still the same than the existing one, but stops at the first modified event,
        - the second one containing newly created events but based on the old events which have been deleted.
        """

        # ----------- ARRANGE --------------

        existing_events = self.env["calendar.event"].search([])
        existing_recurrences = self.env["calendar.recurrence"].search([])

        # event index from where the current recurrence will be splitted/modified
        from_event_index = 3

        # number of events in both recurrences
        old_recurrence_event_count = from_event_index - 1
        new_recurrence_event_count = len(self.recurrent_event_from_outlook_organizer) - from_event_index

        # dates for the new recurrences (shift event dates of 1 day in the past)
        new_rec_first_event_start_date = self.start_date + timedelta(
            days=self.recurrent_event_interval * old_recurrence_event_count - 1
        )
        new_rec_first_event_end_date = new_rec_first_event_start_date + timedelta(hours=1)
        new_rec_end_date = new_rec_first_event_end_date + timedelta(
            days=self.recurrent_event_interval * new_recurrence_event_count - 1
        )

        # prepare first recurrence data in received Outlook events
        events = self.recurrent_event_from_outlook_organizer[0:from_event_index]
        events[0]['lastModifiedDateTime'] = _modified_date_in_the_future(self.recurrent_base_event)
        events[0]['recurrence']['range']['endDate'] = (
            self.recurrence_end_date - timedelta(days=self.recurrent_event_interval * new_recurrence_event_count)
        ).strftime("%Y-%m-%d")

        # prepare second recurrence data in received Outlook events
        events += [
            dict(
                self.recurrent_event_from_outlook_organizer[0],
                start={
                    'dateTime': new_rec_first_event_start_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                end={
                    'dateTime': new_rec_first_event_end_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                id='REC123_new',
                iCalUId='REC456_new',
                recurrence=dict(
                    self.recurrent_event_from_outlook_organizer[0]['recurrence'],
                    range={
                        'startDate': new_rec_first_event_start_date.strftime("%Y-%m-%d"),
                        'endDate': new_rec_end_date.strftime("%Y-%m-%d"),
                        'numberOfOccurrences': 0,
                        'recurrenceTimeZone': 'Romance Standard Time',
                        'type': 'endDate'
                    }
                )
            )
        ]
        # ... and the recurrent events
        events += [
            dict(
                self.recurrent_event_from_outlook_organizer[1],
                start={
                    'dateTime': (
                        new_rec_first_event_start_date + timedelta(days=i * self.recurrent_event_interval)
                    ).strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                end={
                    'dateTime': (
                        new_rec_first_event_end_date + timedelta(days=i * self.recurrent_event_interval)
                    ).strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                id=f'REC123_new_{i+1}',
                iCalUId=f'REC456_new_{i+1}',
                seriesMasterId='REC123_new',
            )
            for i in range(0, new_recurrence_event_count)
        ]
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # ----------- ACT --------------

        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # ----------- ASSERT --------------

        new_events = self.env["calendar.event"].search([]) - existing_events
        new_recurrences = self.env["calendar.recurrence"].search([]) - existing_recurrences

        # old recurrence
        self.assertEqual(len(self.recurrence.calendar_event_ids), 2)
        self.assertEqual(
            self.recurrence.until,
            self.recurrence_end_date.date() - timedelta(days=self.recurrent_event_interval * new_recurrence_event_count)
        )

        # new recurrence
        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(len(new_events), new_recurrence_event_count)
        self.assertEqual(new_recurrences.ms_organizer_event_id, "REC123_new")
        self.assertEqual(new_recurrences.ms_universal_event_id, "REC456_new")

        for i, e in enumerate(sorted(new_events, key=lambda e: e.id)):
            self.assert_odoo_event(e, {
                "start": new_rec_first_event_start_date + timedelta(days=i * self.recurrent_event_interval),
                "stop": new_rec_first_event_end_date + timedelta(days=i * self.recurrent_event_interval),
                "microsoft_id": combine_ids(f'REC123_new_{i+1}', f'REC456_new_{i+1}'),
                "recurrence_id": new_recurrences,
                "follow_recurrence": True,
            })

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_start_of_one_event_and_future_of_recurrence_from_outlook_organizer_calendar_with_overlap(
        self, mock_get_events
    ):
        """
        Update one event start date and future events from a recurrence from Outlook organizer calendar,
        overlapping an existing event.
        """

        # ----------- ARRANGE --------------

        existing_events = self.env["calendar.event"].search([])
        existing_recurrences = self.env["calendar.recurrence"].search([])

        # event index from where the current recurrence will be splitted/modified
        from_event_index = 3

        # number of events in both recurrences
        old_recurrence_event_count = from_event_index - 1
        new_recurrence_event_count = len(self.recurrent_event_from_outlook_organizer) - from_event_index

        # dates for the new recurrences (shift event dates of (recurrent_event_interval + 1) days in the past
        # to overlap an event.
        new_rec_first_event_start_date = self.start_date + timedelta(
            days=self.recurrent_event_interval * (old_recurrence_event_count - 1) - 1
        )
        new_rec_first_event_end_date = new_rec_first_event_start_date + timedelta(hours=1)
        new_rec_end_date = new_rec_first_event_end_date + timedelta(
            days=self.recurrent_event_interval * (new_recurrence_event_count - 1) - 1
        )

        # prepare first recurrence data in received Outlook events
        events = self.recurrent_event_from_outlook_organizer[0:from_event_index]
        events[0]['lastModifiedDateTime'] = _modified_date_in_the_future(self.recurrent_base_event)
        events[0]['recurrence']['range']['endDate'] = (
            self.recurrence_end_date - timedelta(days=self.recurrent_event_interval * new_recurrence_event_count)
        ).strftime("%Y-%m-%d")

        # prepare second recurrence data in received Outlook events
        events += [
            dict(
                self.recurrent_event_from_outlook_organizer[0],
                start={
                    'dateTime': new_rec_first_event_start_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                end={
                    'dateTime': new_rec_first_event_end_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                id='REC123_new',
                iCalUId='REC456_new',
                recurrence=dict(
                    self.recurrent_event_from_outlook_organizer[0]['recurrence'],
                    range={
                        'startDate': new_rec_first_event_start_date.strftime("%Y-%m-%d"),
                        'endDate': new_rec_end_date.strftime("%Y-%m-%d"),
                        'numberOfOccurrences': 0,
                        'recurrenceTimeZone': 'Romance Standard Time',
                        'type': 'endDate'
                    }
                )
            )
        ]
        # ... and the recurrent events
        events += [
            dict(
                self.recurrent_event_from_outlook_organizer[1],
                start={
                    'dateTime': (
                        new_rec_first_event_start_date + timedelta(days=i * self.recurrent_event_interval)
                    ).strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                end={
                    'dateTime': (
                        new_rec_first_event_end_date + timedelta(days=i * self.recurrent_event_interval)
                    ).strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC'
                },
                id=f'REC123_new_{i+1}',
                iCalUId=f'REC456_new_{i+1}',
                seriesMasterId='REC123_new',
            )
            for i in range(0, new_recurrence_event_count)
        ]
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # ----------- ACT --------------

        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # ----------- ASSERT --------------

        new_events = self.env["calendar.event"].search([]) - existing_events
        new_recurrences = self.env["calendar.recurrence"].search([]) - existing_recurrences

        # old recurrence
        self.assertEqual(len(self.recurrence.calendar_event_ids), 2)
        self.assertEqual(
            self.recurrence.until,
            self.recurrence_end_date.date() - timedelta(days=self.recurrent_event_interval * new_recurrence_event_count)
        )

        # new recurrence
        self.assertEqual(len(new_recurrences), 1)
        self.assertEqual(len(new_events), new_recurrence_event_count)
        self.assertEqual(new_recurrences.ms_organizer_event_id, "REC123_new")
        self.assertEqual(new_recurrences.ms_universal_event_id, "REC456_new")

        for i, e in enumerate(sorted(new_events, key=lambda e: e.id)):
            self.assert_odoo_event(e, {
                "start": new_rec_first_event_start_date + timedelta(days=i * self.recurrent_event_interval),
                "stop": new_rec_first_event_end_date + timedelta(days=i * self.recurrent_event_interval),
                "microsoft_id": combine_ids(f'REC123_new_{i+1}', f'REC456_new_{i+1}'),
                "recurrence_id": new_recurrences,
                "follow_recurrence": True,
            })

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_name_of_all_events_of_recurrence_from_outlook_organizer_calendar(self, mock_get_events):
        """
        Update all event names of a recurrence from Outlook organizer calendar.
        """

        # arrange
        new_name = "another event name"
        events = self.recurrent_event_from_outlook_organizer
        for i, e in enumerate(events):
            events[i] = dict(
                e,
                subject=f"{new_name}_{i}",
                lastModifiedDateTime=_modified_date_in_the_future(self.recurrent_base_event)
            )
        ms_events_to_update = {
            events[i]['id']: events[i]['subject'] for i in range(1, len(events))
        }
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # act
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # assert
        updated_events = self.env["calendar.event"].search([
            ('ms_organizer_event_id', 'in', tuple(ms_events_to_update.keys()))
        ])
        for e in updated_events:
            self.assertEqual(e.name, ms_events_to_update[e.ms_organizer_event_id])
            self.assertEqual(e.follow_recurrence, True)

    def _prepare_outlook_events_for_all_events_start_date_update(self, nb_of_events):
        """
        Utility method to avoid repeating data preparation for all tests
        about updating the start date of all events of a recurrence
        """
        new_start_date = datetime(2021, 9, 21, 10, 0, 0)
        new_end_date = new_start_date + timedelta(hours=1)

        # prepare recurrence based on self.recurrent_event_from_outlook_organizer[0] which is the Outlook recurrence
        events = [dict(
            self.recurrent_event_from_outlook_organizer[0],
            start={
                'dateTime': new_start_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                'timeZone': 'UTC'
            },
            end={
                'dateTime': new_end_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                'timeZone': 'UTC',
            },
            recurrence=dict(
                self.recurrent_event_from_outlook_organizer[0]['recurrence'],
                range={
                    'startDate': new_start_date.strftime("%Y-%m-%d"),
                    'endDate': (
                        new_end_date + timedelta(days=self.recurrent_event_interval * nb_of_events)
                    ).strftime("%Y-%m-%d"),
                    'numberOfOccurrences': 0,
                    'recurrenceTimeZone': 'Romance Standard Time',
                    'type': 'endDate'
                }
            ),
            lastModifiedDateTime=_modified_date_in_the_future(self.recurrent_base_event)
        )]

        # prepare all events based on self.recurrent_event_from_outlook_organizer[1] which is the first Outlook event
        events += nb_of_events * [self.recurrent_event_from_outlook_organizer[1]]
        for i in range(1, nb_of_events + 1):
            events[i] = dict(
                events[i],
                id=f'REC123_EVENT_{i}',
                iCalUId=f'REC456_EVENT_{i}',
                start={
                    'dateTime': (
                        new_start_date + timedelta(days=(i - 1) * self.recurrent_event_interval)
                    ).strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC',
                },
                end={
                    'dateTime': (
                        new_end_date + timedelta(days=(i - 1) * self.recurrent_event_interval)
                    ).strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                    'timeZone': 'UTC',
                },
                lastModifiedDateTime=_modified_date_in_the_future(self.recurrent_base_event)
            )

        return events

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_start_of_all_events_of_recurrence_from_outlook_organizer_calendar(self, mock_get_events):
        """
        Update all event start date of a recurrence from Outlook organizer calendar.
        """

        # ----------- ARRANGE -----------
        events = self._prepare_outlook_events_for_all_events_start_date_update(self.recurrent_events_count)
        ms_events_to_update = {
            events[i]['id']: events[i]['start'] for i in range(1, self.recurrent_events_count + 1)
        }
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # ----------- ACT -----------

        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # ----------- ASSERT -----------

        updated_events = self.env["calendar.event"].search([
            ('ms_organizer_event_id', 'in', tuple(ms_events_to_update.keys()))
        ])
        for e in updated_events:
            self.assertEqual(
                e.start.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                ms_events_to_update[e.ms_organizer_event_id]["dateTime"]
            )

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_start_of_all_events_of_recurrence_with_more_events(self, mock_get_events):
        """
        Update all event start date of a recurrence from Outlook organizer calendar, where
        more events have been added (the end date is later in the year)
        """
        # ----------- ARRANGE -----------

        nb_of_events = self.recurrent_events_count + 2
        events = self._prepare_outlook_events_for_all_events_start_date_update(nb_of_events)
        ms_events_to_update = {
            events[i]['id']: events[i]['start'] for i in range(1, nb_of_events + 1)
        }
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # ----------- ACT -----------

        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # ----------- ASSERT -----------

        updated_events = self.env["calendar.event"].search([
            ('ms_organizer_event_id', 'in', tuple(ms_events_to_update.keys()))
        ])
        for e in updated_events:
            self.assertEqual(
                e.start.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                ms_events_to_update[e.ms_organizer_event_id]["dateTime"]
            )

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_start_of_all_events_of_recurrence_with_less_events(self, mock_get_events):
        """
        Update all event start date of a recurrence from Outlook organizer calendar, where
        some events have been removed (the end date is earlier in the year)
        """
        # ----------- ARRANGE -----------

        nb_of_events = self.recurrent_events_count - 2
        events = self._prepare_outlook_events_for_all_events_start_date_update(nb_of_events)
        ms_events_to_update = {
            events[i]['id']: events[i]['start'] for i in range(1, nb_of_events + 1)
        }
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # ----------- ACT -----------

        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # ----------- ASSERT -----------

        updated_events = self.env["calendar.event"].search([
            ('ms_organizer_event_id', 'in', tuple(ms_events_to_update.keys()))
        ])
        for e in updated_events:
            self.assertEqual(
                e.start.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                ms_events_to_update[e.ms_organizer_event_id]["dateTime"]
            )

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_start_of_all_events_of_recurrence_with_exceptions(self, mock_get_events):
        """
        Update all event start date of a recurrence from Outlook organizer calendar, where
        an event does not follow the recurrence anymore (it became an exception)
        """
        # ----------- ARRANGE -----------

        nb_of_events = self.recurrent_events_count - 2
        events = self._prepare_outlook_events_for_all_events_start_date_update(nb_of_events)

        new_start_date = parse(events[2]['start']['dateTime']) + timedelta(days=1)
        new_end_date = parse(events[2]['end']['dateTime']) + timedelta(days=1)
        events[2] = dict(
            events[2],
            start={
                'dateTime': new_start_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                'timeZone': 'UTC',
            },
            end={
                'dateTime': new_end_date.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                'timeZone': 'UTC',
            },
            type="exception",
        )
        ms_events_to_update = {
            events[i]['id']: events[i]['start'] for i in range(1, nb_of_events + 1)
        }
        mock_get_events.return_value = (MicrosoftEvent(events), None)

        # ----------- ACT -----------

        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        # ----------- ASSERT -----------

        updated_events = self.env["calendar.event"].search([
            ('ms_organizer_event_id', 'in', tuple(ms_events_to_update.keys()))
        ])
        for e in updated_events:
            self.assertEqual(
                e.start.strftime("%Y-%m-%dT%H:%M:%S.0000000"),
                ms_events_to_update[e.ms_organizer_event_id]["dateTime"]
            )
