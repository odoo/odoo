# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch, ANY
from datetime import datetime, timedelta

from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_calendar.models.res_users import ResUsers
from odoo.addons.microsoft_calendar.tests.common import TestCommon, mock_get_token, _modified_date_in_the_future, patch_api
from odoo.tests import users

import json
from freezegun import freeze_time


@patch.object(ResUsers, '_get_microsoft_calendar_token', mock_get_token)
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
                    microsoft_id="123",
                    ms_universal_event_id="456",
                )
            )
        (self.organizer_user | self.attendee_user).microsoft_calendar_token_validity = datetime.now() + timedelta(hours=1)

    @patch.object(MicrosoftCalendarService, '_get_single_event')
    @patch.object(MicrosoftCalendarService, 'answer')
    def test_attendee_accepts_event_from_odoo_calendar(self, mock_answer, mock_get_single_event):
        attendee = self.env["calendar.attendee"].search([
            ('event_id', '=', self.simple_event.id),
            ('partner_id', '=', self.attendee_user.partner_id.id)
        ])

        mock_get_single_event.return_value = (True, {'value': [{'id': attendee.event_id.microsoft_id}]})
        attendee.with_user(self.attendee_user).do_accept()
        self.call_post_commit_hooks()
        self.simple_event.invalidate_recordset()

        mock_answer.assert_called_once_with(
            self.simple_event.microsoft_id,
            'accept',
            {"comment": "", "sendResponse": True},
            token=mock_get_token(self.attendee_user),
            timeout=20,
        )

    @patch.object(MicrosoftCalendarService, '_get_single_event')
    @patch.object(MicrosoftCalendarService, 'answer')
    def test_attendee_declines_event_from_odoo_calendar(self, mock_answer, mock_get_single_event):
        attendee = self.env["calendar.attendee"].search([
            ('event_id', '=', self.simple_event.id),
            ('partner_id', '=', self.attendee_user.partner_id.id)
        ])
        mock_get_single_event.return_value = (True, {'value': [{'id': attendee.event_id.microsoft_id}]})
        attendee.with_user(self.attendee_user).do_decline()
        self.call_post_commit_hooks()
        self.simple_event.invalidate_recordset()
        mock_answer.assert_called_once_with(
            self.simple_event.microsoft_id,
            'decline',
            {"comment": "", "sendResponse": True},
            token=mock_get_token(self.attendee_user),
            timeout=20,
        )

    @freeze_time('2021-09-22')
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

    @freeze_time('2021-09-22')
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

    @freeze_time('2021-09-22')
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

    @users('admin')
    def test_sync_data_with_stopped_sync(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        self.env['ir.config_parameter'].sudo().set_param(
            'microsoft_calendar_client_id',
            'test_microsoft_calendar_client_id'
        )
        self.env.user.sudo().microsoft_calendar_rtoken = 'test_microsoft_calendar_rtoken'
        self.env.user.stop_microsoft_synchronization()
        payload = {
            'params': {
                'model': 'calendar.event'
            }
        }
        # Sending the request to the sync_data
        response = self.url_open(
            '/microsoft_calendar/sync_data',
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        ).json()
        # the status must be sync_stopped
        self.assertEqual(response['result']['status'], 'sync_stopped')

    @patch.object(MicrosoftCalendarService, '_get_single_event')
    @patch.object(MicrosoftCalendarService, 'answer')
    def test_answer_event_with_external_organizer(self, mock_answer, mock_get_single_event):
        """ Answer an event invitation from an outsider user and check if it was patched on Outlook side. """
        # Simulate an event that came from an external provider: the organizer isn't registered in Odoo.
        self.simple_event.write({'user_id': False, 'partner_id': False})
        self.simple_event.attendee_ids.state = 'needsAction'

        # Accept the event using the admin account and ensure that answer request is called.
        attendee_ms_organizer_event_id = 100
        mock_get_single_event.return_value = (True, {'value': [{'id': attendee_ms_organizer_event_id}]})
        self.simple_event.attendee_ids[0].with_user(self.organizer_user)._microsoft_sync_event('accept')
        mock_answer.assert_called_once_with(
            attendee_ms_organizer_event_id,
            'accept', {'comment': '', 'sendResponse': True},
            token=mock_get_token(self.organizer_user),
            timeout=20
        )

        # Decline the event using the admin account and ensure that answer request is called.
        self.simple_event.attendee_ids[0].with_user(self.organizer_user)._microsoft_sync_event('decline')
        mock_answer.assert_called_with(
            attendee_ms_organizer_event_id,
            'decline', {'comment': '', 'sendResponse': True},
            token=mock_get_token(self.organizer_user),
            timeout=20
        )
