import json
import requests
from unittest.mock import patch, call, MagicMock

from odoo import fields
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.utils.microsoft_event import MicrosoftEvent
from odoo.addons.microsoft_account.models.microsoft_service import MicrosoftService
from odoo.tests import TransactionCase


DEFAULT_TIMEOUT = 20


class TestMicrosoftService(TransactionCase):

    def _do_request_result(self, data):
        """ _do_request returns a tuple (status, data, time) but only the data part is used """
        return (None, data, None)

    def setUp(self):
        super(TestMicrosoftService, self).setUp()

        self.service = MicrosoftCalendarService(self.env["microsoft.service"])
        self.fake_token = "MY_TOKEN"
        self.fake_sync_token = "MY_SYNC_TOKEN"
        self.fake_next_sync_token = "MY_NEXT_SYNC_TOKEN"
        self.fake_next_sync_token_url = f"https://graph.microsoft.com/v1.0/me/calendarView/delta?$deltatoken={self.fake_next_sync_token}"

        self.header_prefer = 'outlook.body-content-type="html", odata.maxpagesize=50'
        self.header = {'Content-type': 'application/json', 'Authorization': 'Bearer %s' % self.fake_token}
        self.call_with_sync_token = call(
            "/v1.0/me/calendarView/delta",
            {"$deltatoken": self.fake_sync_token},
            {**self.header, 'Prefer': self.header_prefer},
            method="GET", timeout=DEFAULT_TIMEOUT,
        )
        self.call_without_sync_token = call(
            "/v1.0/me/calendarView/delta",
            {
                'startDateTime': fields.Datetime.subtract(fields.Datetime.now(), years=1).strftime("%Y-%m-%dT00:00:00Z"),
                'endDateTime': fields.Datetime.add(fields.Datetime.now(), years=2).strftime("%Y-%m-%dT00:00:00Z"),
            },
            {**self.header, 'Prefer': self.header_prefer},
            method="GET", timeout=DEFAULT_TIMEOUT,
        )

    def test_get_events_delta_without_token(self):
        """
        if no token is provided, an exception is raised
        """
        with self.assertRaises(AttributeError):
            self.service._get_events_delta()

    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_unexpected_exception(self, mock_do_request):
        """
        When an unexpected exception is raised, just propagate it.
        """
        mock_do_request.side_effect = Exception()

        with self.assertRaises(Exception):
            self.service._get_events_delta(token=self.fake_token, timeout=DEFAULT_TIMEOUT)

    @patch.object(MicrosoftCalendarService, "_check_full_sync_required")
    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_delta_token_error(self, mock_do_request, mock_check_full_sync_required):
        """
        When the provided sync token is invalid, an exception should be raised and then
        a full sync should be done.
        """
        mock_do_request.side_effect = [
            requests.HTTPError(response=MagicMock(status_code=410, content="fullSyncRequired")),
            self._do_request_result({"value": []}),
        ]
        mock_check_full_sync_required.return_value = (True)

        events, next_token = self.service._get_events_delta(
            token=self.fake_token, sync_token=self.fake_sync_token, timeout=DEFAULT_TIMEOUT
        )

        self.assertEqual(next_token, None)
        self.assertFalse(events)
        mock_do_request.assert_has_calls([self.call_with_sync_token, self.call_without_sync_token])

    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_delta_without_sync_token(self, mock_do_request):
        """
        when no sync token is provided, a full sync should be done
        """
        # returns empty data without any next sync token
        mock_do_request.return_value = self._do_request_result({"value": []})

        events, next_token = self.service._get_events_delta(token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertEqual(next_token, None)
        self.assertFalse(events)
        mock_do_request.assert_has_calls([self.call_without_sync_token])

    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_delta_with_sync_token(self, mock_do_request):
        """
        when a sync token is provided, we should retrieve the sync token to use for the next sync.
        """
        # returns empty data with a next sync token
        mock_do_request.return_value = self._do_request_result({
            "value": [],
            "@odata.deltaLink": self.fake_next_sync_token_url
        })

        events, next_token = self.service._get_events_delta(
            token=self.fake_token, sync_token=self.fake_sync_token, timeout=DEFAULT_TIMEOUT
        )

        self.assertEqual(next_token, "MY_NEXT_SYNC_TOKEN")
        self.assertFalse(events)
        mock_do_request.assert_has_calls([self.call_with_sync_token])

    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_one_page(self, mock_do_request):
        """
        When all events are on one page, just get them.
        """
        mock_do_request.return_value = self._do_request_result({
            "value": [
                {"id": 1, "type": "singleInstance", "subject": "ev1"},
                {"id": 2, "type": "singleInstance", "subject": "ev2"},
                {"id": 3, "type": "singleInstance", "subject": "ev3"},
            ],
        })
        events, _ = self.service._get_events_delta(token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertEqual(events, MicrosoftEvent([
            {"id": 1, "type": "singleInstance", "subject": "ev1"},
            {"id": 2, "type": "singleInstance", "subject": "ev2"},
            {"id": 3, "type": "singleInstance", "subject": "ev3"},
        ]))
        mock_do_request.assert_has_calls([self.call_without_sync_token])

    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_loop_over_pages(self, mock_do_request):
        """
        Loop over pages to retrieve all the events.
        """
        mock_do_request.side_effect = [
            self._do_request_result({
                "value": [{"id": 1, "type": "singleInstance", "subject": "ev1"}],
                "@odata.nextLink": "link_1"
            }),
            self._do_request_result({
                "value": [{"id": 2, "type": "singleInstance", "subject": "ev2"}],
                "@odata.nextLink": "link_2"
            }),
            self._do_request_result({
                "value": [{"id": 3, "type": "singleInstance", "subject": "ev3"}],
            }),
        ]

        events, _ = self.service._get_events_delta(token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertEqual(events, MicrosoftEvent([
            {"id": 1, "type": "singleInstance", "subject": "ev1"},
            {"id": 2, "type": "singleInstance", "subject": "ev2"},
            {"id": 3, "type": "singleInstance", "subject": "ev3"},
        ]))
        mock_do_request.assert_has_calls([
            self.call_without_sync_token,
            call(
                "link_1",
                {},
                {**self.header, 'Prefer': self.header_prefer},
                preuri='', method="GET", timeout=DEFAULT_TIMEOUT
            ),
            call(
                "link_2",
                {},
                {**self.header, 'Prefer': self.header_prefer},
                preuri='', method="GET", timeout=DEFAULT_TIMEOUT
            ),
        ])

    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_filter_out_occurrences(self, mock_do_request):
        """
        When all events are on one page, just get them.
        """
        mock_do_request.return_value = self._do_request_result({
            "value": [
                {"id": 1, "type": "singleInstance", "subject": "ev1"},
                {"id": 2, "type": "occurrence", "subject": "ev2"},
                {"id": 3, "type": "seriesMaster", "subject": "ev3"},
            ],
        })
        events, _ = self.service._get_events_delta(token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertEqual(events, MicrosoftEvent([
            {"id": 1, "type": "singleInstance", "subject": "ev1"},
            {"id": 3, "type": "seriesMaster", "subject": "ev3"},
        ]))
        mock_do_request.assert_has_calls([self.call_without_sync_token])

    def test_get_occurrence_details_token_error(self):
        """
        if no token is provided, an exception is raised
        """
        with self.assertRaises(AttributeError):
            self.service._get_occurrence_details(1)

    @patch.object(MicrosoftService, "_do_request")
    def test_get_occurrence_details(self, mock_do_request):
        mock_do_request.return_value = self._do_request_result({
            "value": [
                {"id": 1, "type": "singleInstance", "subject": "ev1"},
                {"id": 2, "type": "occurrence", "subject": "ev2"},
                {"id": 3, "type": "seriesMaster", "subject": "ev3"},
            ],
        })
        events = self.service._get_occurrence_details(123, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertEqual(events, MicrosoftEvent([
            {"id": 1, "type": "singleInstance", "subject": "ev1"},
            {"id": 2, "type": "occurrence", "subject": "ev2"},
            {"id": 3, "type": "seriesMaster", "subject": "ev3"},
        ]))

        mock_do_request.assert_called_with(
            "/v1.0/me/events/123/instances",
            {
                'startDateTime': fields.Datetime.subtract(fields.Datetime.now(), years=1).strftime("%Y-%m-%dT00:00:00Z"),
                'endDateTime': fields.Datetime.add(fields.Datetime.now(), years=2).strftime("%Y-%m-%dT00:00:00Z"),
            },
            {**self.header, 'Prefer': self.header_prefer},
            method='GET', timeout=DEFAULT_TIMEOUT,
        )

    def test_get_events_token_error(self):
        """
        if no token is provided, an exception is raised
        """
        with self.assertRaises(AttributeError):
            self.service.get_events()

    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_no_serie_master(self, mock_do_request):
        """
        When there is no serie master, just retrieve the list of events.
        """
        mock_do_request.return_value = self._do_request_result({
            "value": [
                {"id": 1, "type": "singleInstance", "subject": "ev1"},
                {"id": 2, "type": "singleInstance", "subject": "ev2"},
                {"id": 3, "type": "singleInstance", "subject": "ev3"},
            ],
        })

        events, _ = self.service.get_events(token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertEqual(events, MicrosoftEvent([
            {"id": 1, "type": "singleInstance", "subject": "ev1"},
            {"id": 2, "type": "singleInstance", "subject": "ev2"},
            {"id": 3, "type": "singleInstance", "subject": "ev3"},
        ]))

    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_with_one_serie_master(self, mock_do_request):
        """
        When there is a serie master, retrieve the list of events and event occurrences linked to the serie master
        """
        mock_do_request.side_effect = [
            self._do_request_result({
                "value": [
                    {"id": 1, "type": "singleInstance", "subject": "ev1"},
                    {"id": 2, "type": "seriesMaster", "subject": "ev2"},
                ],
            }),
            self._do_request_result({
                "value": [
                    {"id": 3, "type": "occurrence", "subject": "ev3"},
                ],
            }),
        ]

        events, _ = self.service.get_events(token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertEqual(events, MicrosoftEvent([
            {"id": 1, "type": "singleInstance", "subject": "ev1"},
            {"id": 2, "type": "seriesMaster", "subject": "ev2"},
            {"id": 3, "type": "occurrence", "subject": "ev3"},
        ]))

    def test_insert_token_error(self):
        """
        if no token is provided, an exception is raised
        """
        with self.assertRaises(AttributeError):
            self.service.insert({})


    @patch.object(MicrosoftService, "_do_request")
    def test_insert(self, mock_do_request):

        mock_do_request.return_value = self._do_request_result({'id': 1, 'iCalUId': 2})

        instance_id, event_id = self.service.insert({"subject": "ev1"}, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertEqual(instance_id, 1)
        self.assertEqual(event_id, 2)
        mock_do_request.assert_called_with(
            "/v1.0/me/calendar/events",
            json.dumps({"subject": "ev1"}),
            self.header, method="POST", timeout=DEFAULT_TIMEOUT
        )

    def test_patch_token_error(self):
        """
        if no token is provided, an exception is raised
        """
        with self.assertRaises(AttributeError):
            self.service.patch(123, {})

    @patch.object(MicrosoftService, "_do_request")
    def test_patch_returns_false_if_event_does_not_exist(self, mock_do_request):
        event_id = 123
        values = {"subject": "ev2"}
        mock_do_request.return_value = (404, "", None)

        res = self.service.patch(event_id, values, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertFalse(res)
        mock_do_request.assert_called_with(
            f"/v1.0/me/calendar/events/{event_id}",
            json.dumps(values),
            self.header, method="PATCH", timeout=DEFAULT_TIMEOUT
        )

    @patch.object(MicrosoftService, "_do_request")
    def test_patch_an_existing_event(self, mock_do_request):
        event_id = 123
        values = {"subject": "ev2"}
        mock_do_request.return_value = (200, "", None)

        res = self.service.patch(event_id, values, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertTrue(res)
        mock_do_request.assert_called_with(
            f"/v1.0/me/calendar/events/{event_id}",
            json.dumps(values),
            self.header, method="PATCH", timeout=DEFAULT_TIMEOUT
        )

    def test_delete_token_error(self):
        """
        if no token is provided, an exception is raised
        """
        with self.assertRaises(AttributeError):
            self.service.delete(123)

    @patch.object(MicrosoftService, "_do_request")
    def test_delete_returns_false_if_event_does_not_exist(self, mock_do_request):
        event_id = 123
        mock_do_request.return_value = (404, "", None)

        res = self.service.delete(event_id, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertFalse(res)
        mock_do_request.assert_called_with(
            f"/v1.0/me/calendar/events/{event_id}",
            {}, headers={'Authorization': 'Bearer %s' % self.fake_token}, method="DELETE", timeout=DEFAULT_TIMEOUT
        )

    @patch.object(MicrosoftService, "_do_request")
    def test_delete_an_already_cancelled_event(self, mock_do_request):
        """
        When an event has already been cancelled, Outlook may return a status code equals to 403 or 410.
        In this case, the delete method should return True.
        """
        event_id = 123

        for status in (403, 410):
            mock_do_request.return_value = (status, "", None)

            res = self.service.delete(event_id, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

            self.assertTrue(res)
            mock_do_request.assert_called_with(
                f"/v1.0/me/calendar/events/{event_id}",
                {}, headers={'Authorization': 'Bearer %s' % self.fake_token}, method="DELETE", timeout=DEFAULT_TIMEOUT
            )


    @patch.object(MicrosoftService, "_do_request")
    def test_delete_an_existing_event(self, mock_do_request):
        event_id = 123
        mock_do_request.return_value = (200, "", None)

        res = self.service.delete(event_id, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertTrue(res)
        mock_do_request.assert_called_with(
            f"/v1.0/me/calendar/events/{event_id}",
            {}, headers={'Authorization': 'Bearer %s' % self.fake_token}, method="DELETE", timeout=DEFAULT_TIMEOUT
        )

    def test_answer_token_error(self):
        """
        if no token is provided, an exception is raised
        """
        with self.assertRaises(AttributeError):
            self.service.answer(123, 'ok', {})

    @patch.object(MicrosoftService, "_do_request")
    def test_answer_returns_false_if_event_does_not_exist(self, mock_do_request):
        event_id = 123
        answer = "accept"
        values = {"a": 1, "b": 2}
        mock_do_request.return_value = (404, "", None)

        res = self.service.answer(event_id, answer, values, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertFalse(res)
        mock_do_request.assert_called_with(
            f"/v1.0/me/calendar/events/{event_id}/{answer}",
            json.dumps(values),
            self.header, method="POST", timeout=DEFAULT_TIMEOUT
        )

    @patch.object(MicrosoftService, "_do_request")
    def test_answer_to_an_existing_event(self, mock_do_request):
        event_id = 123
        answer = "decline"
        values = {"a": 1, "b": 2}
        mock_do_request.return_value = (200, "", None)

        res = self.service.answer(event_id, answer, values, token=self.fake_token, timeout=DEFAULT_TIMEOUT)

        self.assertTrue(res)
        mock_do_request.assert_called_with(
            f"/v1.0/me/calendar/events/{event_id}/{answer}",
            json.dumps(values),
            self.header, method="POST", timeout=DEFAULT_TIMEOUT
        )

    @patch.object(MicrosoftCalendarService, "_check_full_sync_required")
    @patch.object(MicrosoftService, "_do_request")
    def test_get_events_delta_with_outdated_sync_token(self, mock_do_request, mock_check_full_sync_required):
        """ When an outdated sync token is provided, we must fetch all events again for updating the old token. """
        # Throw a 'HTTPError' when the token is outdated, thus triggering the fetching of all events.
        # Simulate a scenario which the full sync is required, such as when getting the 'SyncStateNotFound' error code.
        mock_do_request.side_effect = [
            requests.HTTPError(response=MagicMock(status_code=410, error={'code': "SyncStateNotFound"})),
            self._do_request_result({"value": []}),
        ]
        mock_check_full_sync_required.return_value = (True)

        # Call the regular 'delta' get events with an outdated token for triggering the all events fetching.
        self.env.user.microsoft_calendar_sync_token = self.fake_sync_token
        self.service._get_events_delta(token=self.fake_token, sync_token=self.fake_sync_token, timeout=DEFAULT_TIMEOUT)

        # Two calls must have been made: one call with the outdated sync token and another one with no sync token.
        mock_do_request.assert_has_calls([
            self.call_with_sync_token,
            self.call_without_sync_token
        ])
