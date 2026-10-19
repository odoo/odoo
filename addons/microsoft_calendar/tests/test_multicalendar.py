# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch, ANY

from odoo.addons.mail.tests.common import MailCase
from odoo.addons.microsoft_calendar.models.res_users import ResUsers
from odoo.addons.microsoft_calendar.tests.common import TestCommon, mock_get_token, _modified_date_in_the_future, patch_api
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent

from odoo.tests import tagged, users


@tagged('at_install', '-post_install')  # LEGACY at_install
@patch.object(ResUsers, '_get_microsoft_calendar_token', mock_get_token)
class TestMultiCalendar(TestCommon, MailCase):

    def setUp(self):
        super().setUp()
        self.secondary_calendar = self.env["calendar.calendar"].with_user(self.organizer_user).create({"name": "Secondary Calendar"})

    @patch_api
    @users('mike@organizer.com')
    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_update_does_not_overwrite_falsy_calendar_id(self, mock_get_events):
        """
        If the user creates a calendarless event (calendar_id=False), a later sync from outlook
        must not populate/overwrite calendar_id based on the organizer.
        """
        # arrange
        event = self.env["calendar.event"].create(
            dict(
                self.simple_event_values,
                calendar_id=False,
            )
        )
        self.call_post_commit_hooks()
        event.invalidate_recordset()

        mock_get_events.return_value = (
            MicrosoftEvent([dict(
                self.simple_event_from_outlook_organizer,
                lastModifiedDateTime=_modified_date_in_the_future(event)
            )]), None
        )

        self.organizer_user.sudo()._sync_microsoft_calendar()

        # assert
        self.assertFalse(event.calendar_id, "calendar_id must remain falsy after sync")

    @users('mike@organizer.com')
    @patch.object(MicrosoftCalendarService, 'get_events')
    @patch.object(MicrosoftCalendarService, 'delete')
    @patch.object(MicrosoftCalendarService, 'insert')
    def test_moving_an_event_to_a_secondary_calendar_removes_it_from_outlook(self, mock_insert, mock_delete, mock_get_events):
        """
        Outlook sync only covers the user's primary calendar. Moving a previously
        synced event onto a secondary calendar should delete it from Outlook and
        clear its Microsoft ids (rather than patch/update it there).
        """
        # arrange - Create an event in Odoo and ensure that it was inserted to outlook
        event_id = "123"
        event_iCalUId = "456"
        mock_insert.return_value = (event_id, event_iCalUId)
        event = self.env["calendar.event"].create(self.simple_event_values)
        self.call_post_commit_hooks()
        event.invalidate_recordset()
        mock_insert.assert_called_once()

        # act - Move the event to the secondary calendar
        event.write({"calendar_id": self.secondary_calendar.id})
        self.call_post_commit_hooks()
        event.invalidate_recordset()

        # assert - Ensure that the event was deleted from Outlook
        mock_delete.assert_called_once_with(
            event_id,
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )

        self.assertFalse(event.microsoft_id)
        self.assertFalse(event.ms_universal_event_id)

        # Ensure that a subsequent sync does not delete the event from Odoo, and it doesn't reinsert it in Outlook.
        mock_get_events.return_value = (
            MicrosoftEvent([{
                "id": event_id,
                "@removed": {"reason": "deleted"}
            }]),
            None
        )
        self.organizer_user.sudo()._sync_microsoft_calendar()
        self.assertTrue(event.exists())

        # Event was not inserted again
        mock_insert.assert_called_once()
        self.assertEqual(event.need_sync_m, False)
