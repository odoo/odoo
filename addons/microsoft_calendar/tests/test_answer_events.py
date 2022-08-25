# -*- coding: utf-8 -*-
from unittest.mock import patch, ANY

from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.models.res_users import User
from odoo.addons.microsoft_calendar.utils.event_id_storage import combine_ids
from odoo.addons.microsoft_calendar.tests.common import TestCommon, mock_get_token, _modified_date_in_the_future, patch_api


@patch.object(User, '_get_microsoft_calendar_token', mock_get_token)
class TestAnswerEvents(TestCommon):

    @patch_api
    def setUp(self):
        super().setUp()

        # a simple event
        self.simple_event = self.env["calendar.event"].search([("name", "=", "simple_event")])
        if not self.simple_event:
            self.simple_event = self.env["calendar.event"].with_user(self.organizer_user).create(
                dict(
                    self.simple_event_values,
                    microsoft_id=combine_ids("123", "456"),
                )
            )

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_attendee_accepts_event_from_odoo_calendar(self, mock_patch):
        attendee = self.env["calendar.attendee"].search([
            ('event_id', '=', self.simple_event.id),
            ('partner_id', '=', self.attendee_user.partner_id.id)
        ])

        attendee.with_user(self.attendee_user).do_accept()
        self.call_post_commit_hooks()
        self.simple_event.invalidate_recordset()

        mock_patch.assert_called_once_with(
            self.simple_event.ms_organizer_event_id,
            {
                "attendees": [{
                    'emailAddress': {'address': attendee.email or '', 'name': attendee.display_name or ''},
                    'status': {'response': 'accepted'}
                }]
            },
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )

    @patch.object(MicrosoftCalendarService, 'patch')
    def test_attendee_declines_event_from_odoo_calendar(self, mock_patch):
        attendee = self.env["calendar.attendee"].search([
            ('event_id', '=', self.simple_event.id),
            ('partner_id', '=', self.attendee_user.partner_id.id)
        ])

        attendee.with_user(self.attendee_user).do_decline()
        self.call_post_commit_hooks()
        self.simple_event.invalidate_recordset()

        mock_patch.assert_called_once_with(
            self.simple_event.ms_organizer_event_id,
            {
                "attendees": [{
                    'emailAddress': {'address': attendee.email or '', 'name': attendee.display_name or ''},
                    'status': {'response': 'declined'}
                }]
            },
            token=mock_get_token(self.organizer_user),
            timeout=ANY,
        )

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_attendee_accepts_event_from_outlook_calendar(self, mock_get_events):
        """
        In his Outlook calendar, the attendee accepts the event and sync with his odoo calendar.
        """
        mock_get_events.return_value = (
            MicrosoftEvent([dict(
                self.simple_event_from_outlook_organizer,
                attendees=[{
                    'type': 'required',
                    'status': {'response': 'accepted', 'time': '0001-01-01T00:00:00Z'},
                    'emailAddress': {'name': self.attendee_user.display_name, 'address': self.attendee_user.email}
                }],
                lastModifiedDateTime=_modified_date_in_the_future(self.simple_event)
            )]), None
        )
        self.attendee_user.with_user(self.attendee_user).sudo()._sync_microsoft_calendar()

        attendee = self.env["calendar.attendee"].search([
            ('event_id', '=', self.simple_event.id),
            ('partner_id', '=', self.attendee_user.partner_id.id)
        ])
        self.assertEqual(attendee.state, "accepted")

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_attendee_accepts_event_from_outlook_calendar_synced_by_organizer(self, mock_get_events):
        """
        In his Outlook calendar, the attendee accepts the event and the organizer syncs his odoo calendar.
        """
        mock_get_events.return_value = (
            MicrosoftEvent([dict(
                self.simple_event_from_outlook_organizer,
                attendees=[{
                    'type': 'required',
                    'status': {'response': 'accepted', 'time': '0001-01-01T00:00:00Z'},
                    'emailAddress': {'name': self.attendee_user.display_name, 'address': self.attendee_user.email}
                }],
                lastModifiedDateTime=_modified_date_in_the_future(self.simple_event)
            )]), None
        )
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        attendee = self.env["calendar.attendee"].search([
            ('event_id', '=', self.simple_event.id),
            ('partner_id', '=', self.attendee_user.partner_id.id)
        ])
        self.assertEqual(attendee.state, "accepted")

    def test_attendee_declines_event_from_outlook_calendar(self):
        """
        In his Outlook calendar, the attendee declines the event leading to automatically
        delete this event (that's the way Outlook handles it ...)

        LIMITATION:

        But, as there is no way to get the iCalUId to identify the corresponding Odoo event,
        there is no way to update the attendee status to "declined".
        """

    @patch.object(MicrosoftCalendarService, 'get_events')
    def test_attendee_declines_event_from_outlook_calendar_synced_by_organizer(self, mock_get_events):
        """
        In his Outlook calendar, the attendee declines the event leading to automatically
        delete this event (that's the way Outlook handles it ...)
        """
        mock_get_events.return_value = (
            MicrosoftEvent([dict(
                self.simple_event_from_outlook_organizer,
                attendees=[{
                    'type': 'required',
                    'status': {'response': 'declined', 'time': '0001-01-01T00:00:00Z'},
                    'emailAddress': {'name': self.attendee_user.display_name, 'address': self.attendee_user.email}
                }],
                lastModifiedDateTime=_modified_date_in_the_future(self.simple_event)
            )]), None
        )
        self.organizer_user.with_user(self.organizer_user).sudo()._sync_microsoft_calendar()

        attendee = self.env["calendar.attendee"].search([
            ('event_id', '=', self.simple_event.id),
            ('partner_id', '=', self.attendee_user.partner_id.id)
        ])
        self.assertEqual(attendee.state, "declined")
