"""Python-side tests for the AutoCompleteController parsing logic.

The pre-existing UI suite (test_ui.py) is bound to the demo environment
(admin/admin credentials, demo-database record ids, a browser tour) and
cannot run on production-clone databases. These tests pin the same
business behavior — translating Google Places payloads into standard
address fields — directly on the controller, with the HTTP layer mocked.
"""

from contextlib import contextmanager
from unittest.mock import patch

import requests

from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged

from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import (
    AutoCompleteController,
)

CONTROLLER_MODULE = (
    "odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete"
)


@tagged("post_install", "-at_install")
class TestAutocompleteControllerParsing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.controller = AutoCompleteController()
        cls.us = cls.env.ref("base.us")
        cls.us_state = cls.env["res.country.state"].search(
            [("country_id", "=", cls.us.id)], limit=1
        )

    @contextmanager
    def _mock_request(self):
        """Patch the module-level ``request`` with a stub exposing our env."""
        test_env = self.env

        class _RequestStub:
            env = test_env

        with patch(f"{CONTROLLER_MODULE}.request", _RequestStub()):
            yield

    def _complete_search(self, payload, address="9 rue de Bourlottes, Ramillies"):
        with (
            self._mock_request(),
            patch.object(
                AutoCompleteController,
                "_call_google_route",
                lambda _controller, _route, _params: payload,
            ),
        ):
            return self.controller._perform_complete_place_search(
                address, api_key="key", google_place_id="place"
            )

    # ------------------------------------------------------------------
    # _translate_google_to_standard
    # ------------------------------------------------------------------
    def test_translate_resolves_country_and_state(self):
        """Country resolves by code and the state binds to that country."""
        if not self.us_state:
            self.skipTest("no US states in this database")
        fields = [
            {"type": "country", "short_name": "us", "long_name": "ignored"},
            {
                "type": "administrative_area_level_1",
                "short_name": self.us_state.code,
                "long_name": self.us_state.name,
            },
        ]
        with self._mock_request():
            data = self.controller._translate_google_to_standard(fields)
        self.assertEqual(data["country"], [self.us.id, self.us.name])
        self.assertEqual(data["state"], [self.us_state.id, self.us_state.name])

    def test_translate_state_before_country_is_skipped(self):
        """A state field arriving before any country cannot be resolved."""
        fields = [
            {
                "type": "administrative_area_level_1",
                "short_name": "XX",
                "long_name": "Somewhere",
            }
        ]
        with self._mock_request():
            data = self.controller._translate_google_to_standard(fields)
        self.assertNotIn("state", data)
        # The same google field also feeds 'city' as fallback.
        self.assertEqual(data["city"], "Somewhere")

    def test_translate_first_assignment_wins(self):
        """Once a standard field has a value, later google fields keep out."""
        fields = [
            {"type": "locality", "short_name": "R", "long_name": "Ramillies"},
            {
                "type": "administrative_area_level_2",
                "short_name": "BW",
                "long_name": "Brabant",
            },
        ]
        with self._mock_request():
            data = self.controller._translate_google_to_standard(fields)
        self.assertEqual(data["city"], "Ramillies")

    # ------------------------------------------------------------------
    # _guess_number_from_input
    # ------------------------------------------------------------------
    def test_guess_number_strips_known_address_parts(self):
        """The house number is recovered from the raw input."""
        guessed = self.controller._guess_number_from_input(
            "9 rue de Bourlottes, 1367 Ramillies",
            {"street": "rue de Bourlottes", "city": "Ramillies", "zip": "1367"},
        )
        self.assertEqual(guessed, "9")

    # ------------------------------------------------------------------
    # _perform_place_search
    # ------------------------------------------------------------------
    def test_place_search_short_input_returns_empty(self):
        """Inputs at or below the minimal size never hit the API (boundary)."""
        with self._mock_request():
            res = self.controller._perform_place_search(
                "abc", api_key="key", session_id="sess"
            )
        self.assertEqual(res, {"results": [], "session_id": "sess"})

    def test_place_search_maps_predictions(self):
        """Google predictions map to formatted_address/google_place_id pairs."""
        payload = {
            "predictions": [
                {"description": "Paris, France", "place_id": "PARIS"},
                {"description": "Paris, TX, USA", "place_id": "PARIS_TX"},
            ]
        }
        with (
            self._mock_request(),
            patch.object(
                AutoCompleteController,
                "_call_google_route",
                lambda _controller, _route, _params: payload,
            ),
        ):
            res = self.controller._perform_place_search(
                "Paris, somewhere", api_key="key", session_id="sess"
            )
        self.assertEqual(
            res["results"],
            [
                {"formatted_address": "Paris, France", "google_place_id": "PARIS"},
                {"formatted_address": "Paris, TX, USA", "google_place_id": "PARIS_TX"},
            ],
        )
        self.assertEqual(res["session_id"], "sess")

    def test_place_search_timeout_returns_empty(self):
        """A google-side timeout degrades to an empty result set (boundary).

        Raises the real ``requests.exceptions.ConnectTimeout`` here, not the
        builtin ``TimeoutError`` — the two are unrelated exception hierarchies
        and only the former is what ``requests.get`` actually raises.
        """

        def _raise_timeout(_controller, _route, _params):
            raise requests.exceptions.ConnectTimeout("google is down")

        with (
            self._mock_request(),
            patch.object(AutoCompleteController, "_call_google_route", _raise_timeout),
        ):
            res = self.controller._perform_place_search(
                "Paris, somewhere", api_key="key", session_id="sess"
            )
        self.assertEqual(res, {"results": [], "session_id": "sess"})

    def test_place_search_real_requests_timeout_returns_empty(self):
        """A real ``requests`` timeout (not the builtin) also degrades gracefully.

        ``requests.exceptions.Timeout``/``ReadTimeout``/``ConnectTimeout`` do
        not subclass the builtin ``TimeoutError``, so this exercises
        ``requests.get`` itself rather than mocking ``_call_google_route``
        away — the gap the previous test alone left uncovered.
        """
        with (
            self._mock_request(),
            patch.object(
                GuardedSession,
                "request",
                side_effect=requests.exceptions.ReadTimeout("google is down"),
            ),
        ):
            res = self.controller._perform_place_search(
                "Paris, somewhere", api_key="key", session_id="sess"
            )
        self.assertEqual(res, {"results": [], "session_id": "sess"})

    def test_place_search_failure_does_not_log_the_api_key(self):
        """The credential must never reach the log.

        A connection-level ``requests`` exception stringifies to the whole
        outgoing URL, and ours carries ``key=<api key>`` in the query string,
        so logging the exception verbatim published the credential. Raise an
        exception shaped exactly like the real one and assert the key is absent
        from every record the controller emits.
        """
        secret = "AIza_TEST_KEY_DO_NOT_LOG"
        realistic = requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='maps.googleapis.com', port=443): "
            "Max retries exceeded with url: /maps/api/place/autocomplete/json"
            f"?key={secret}&input=Ramillies (Caused by NewConnectionError(...))"
        )

        def _raise(_controller, _route, _params):
            raise realistic

        with (
            self._mock_request(),
            patch.object(AutoCompleteController, "_call_google_route", _raise),
            self.assertLogs(CONTROLLER_MODULE, level="ERROR") as captured,
        ):
            res = self.controller._perform_place_search(
                "Ramillies, somewhere", api_key=secret, session_id="sess"
            )

        self.assertEqual(res, {"results": [], "session_id": "sess"})
        self.assertTrue(captured.output, "the failure must still be logged")
        for line in captured.output:
            self.assertNotIn(secret, line, "the API key leaked into the log")
        self.assertIn("ConnectionError", "".join(captured.output))

    def test_complete_search_failure_does_not_log_the_api_key(self):
        """Same guarantee on the details route."""
        secret = "AIza_TEST_KEY_DO_NOT_LOG"
        realistic = requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='maps.googleapis.com', port=443): "
            "Max retries exceeded with url: /maps/api/place/details/json"
            f"?key={secret}&place_id=abc (Caused by NewConnectionError(...))"
        )

        def _raise(_controller, _route, _params):
            raise realistic

        with (
            self._mock_request(),
            patch.object(AutoCompleteController, "_call_google_route", _raise),
            self.assertLogs(CONTROLLER_MODULE, level="ERROR") as captured,
        ):
            res = self.controller._perform_complete_place_search(
                "9 rue de Bourlottes", api_key=secret, google_place_id="abc"
            )

        self.assertEqual(res, {"address": None})
        for line in captured.output:
            self.assertNotIn(secret, line, "the API key leaked into the log")

    # ------------------------------------------------------------------
    # _perform_complete_place_search
    # ------------------------------------------------------------------
    def test_complete_search_full_payload(self):
        """A full details payload lands in the standard address fields."""
        res = self._complete_search(
            {
                "result": {
                    "adr_address": (
                        '<span class="street-address">9 rue de Bourlottes</span>,'
                        " <span>1367 Ramillies</span>"
                    ),
                    "address_components": [
                        {
                            "long_name": "9",
                            "short_name": "9",
                            "types": ["street_number"],
                        },
                        {
                            "long_name": "rue de Bourlottes",
                            "short_name": "r. B.",
                            "types": ["route"],
                        },
                        {
                            "long_name": "Ramillies",
                            "short_name": "R",
                            "types": ["locality", "political"],
                        },
                        {
                            "long_name": "1367",
                            "short_name": "1367",
                            "types": ["postal_code"],
                        },
                    ],
                },
                "status": "OK",
            }
        )
        self.assertEqual(res["number"], "9")
        self.assertEqual(res["street"], "rue de Bourlottes")
        self.assertEqual(res["city"], "Ramillies")
        self.assertEqual(res["zip"], "1367")
        self.assertEqual(res["formatted_street_number"], "9 rue de Bourlottes")

    def test_complete_search_missing_number_is_guessed(self):
        """Without a street_number component the number comes from the input."""
        res = self._complete_search(
            {
                "result": {
                    "adr_address": "",
                    "address_components": [
                        {
                            "long_name": "rue de Bourlottes",
                            "short_name": "r. B.",
                            "types": ["route"],
                        },
                        {
                            "long_name": "Ramillies",
                            "short_name": "R",
                            "types": ["locality"],
                        },
                    ],
                },
                "status": "OK",
            }
        )
        self.assertEqual(res["number"], "9")
        self.assertEqual(res["formatted_street_number"], "9 rue de Bourlottes")

    def test_complete_search_malformed_payload_returns_none(self):
        """A payload without result/address_components degrades gracefully."""
        self.assertEqual(self._complete_search({"status": "OK"}), {"address": None})

    def test_address_full_without_a_key_makes_no_outbound_call(self):
        """With no key configured the details route must not call Google (A02)."""
        calls = []

        def _spy(_controller, route, _params):
            calls.append(route)
            raise AssertionError("no outbound call should be made")

        with (
            self._mock_request(),
            patch.object(AutoCompleteController, "_get_api_key", lambda *_a: False),
            patch.object(AutoCompleteController, "_call_google_route", _spy),
        ):
            res = self.controller._autocomplete_address_full(
                "9 rue de Bourlottes", google_place_id="abc"
            )
        self.assertEqual(res, {"address": None})
        self.assertEqual(calls, [], "the route called Google with no key")

    def test_complete_search_skips_components_without_types(self):
        """A malformed component degrades like a malformed payload (A03).

        The try/except above the loop already turns a payload with no
        ``result``/``address_components`` into ``{"address": None}``; before
        this, a component missing ``types`` raised ``KeyError`` and one with an
        empty list raised ``IndexError`` three lines later, escaping the
        jsonrpc route as a 500.
        """
        for label, component in (
            ("missing key", {"long_name": "1", "short_name": "1"}),
            ("empty list", {"long_name": "1", "short_name": "1", "types": []}),
        ):
            with self.subTest(label):
                res = self._complete_search(
                    {
                        "result": {
                            "adr_address": "<span>1 X St</span>, Y",
                            "address_components": [component],
                        }
                    }
                )
                self.assertIsInstance(res, dict, "must not raise")

    def test_complete_search_keeps_well_formed_components(self):
        """The skip must not swallow usable components alongside a broken one."""
        res = self._complete_search(
            {
                "result": {
                    "adr_address": "<span>9 rue de Bourlottes</span>, Ramillies",
                    "address_components": [
                        {"long_name": "junk", "short_name": "junk"},
                        {
                            "long_name": "rue de Bourlottes",
                            "short_name": "rue de Bourlottes",
                            "types": ["route"],
                        },
                    ],
                }
            }
        )
        self.assertEqual(res.get("street"), "rue de Bourlottes")
