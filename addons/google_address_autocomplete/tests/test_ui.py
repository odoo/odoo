# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo.tools import mute_logger

from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import (
    AutoCompleteController,
)
from .mock_google_places import make_mock_google_route

from odoo.tests import patch, HttpCase, tagged

CONTROLLER_PATH = "odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete.AutoCompleteController"
MOCK_GOOGLE_ID = "aHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g/dj1kUXc0dzlXZ1hjUQ=="
MOCK_API_KEY = "Tm9ib2R5IGV4cGVjdHMgdGhlIFNwYW5pc2ggaW5xdWlzaXRpb24gIQ=="


@tagged("post_install", "-at_install")
class TestUI(HttpCase):
    def test_address_autocomplete(self):
        with patch.object(
            AutoCompleteController,
            "_perform_complete_place_search",
            lambda controller, *args, **kwargs: {
                "country": [
                    self.env["res.country"].search([("code", "=", "USA")]).id,
                    "United States",
                ],
                "state": [
                    self.env["res.country.state"]
                    .search([("country_id.code", "=", "USA")])[0]
                    .id,
                    "Alabama",
                ],
                "zip": "12345",
                "city": "A Fictional City",
                "street": "A fictional Street",
                "street2": "A fictional Street 2",
                "number": 42,
                "formatted_street_number": "42 A fictional Street",
            },
        ), patch.object(
            AutoCompleteController,
            "_perform_place_search",
            lambda controller, *args, **kwargs: {
                "results": [
                    {
                        "formatted_address": f"Result {x}",
                        "google_place_id": MOCK_GOOGLE_ID,
                    }
                    for x in range(5)
                ]
            },
        ):
            self.env["ir.config_parameter"].sudo().set_param(
                "google_address_autocomplete.google_places_api_key", MOCK_API_KEY
            )
            self.start_tour(
                "/odoo/companies", "autocomplete_address_tour", login="admin"
            )

    def test_google_api_calls(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "google_address_autocomplete.google_places_api_key", MOCK_API_KEY
        )

        steps = []

        def on_route(route, params):
            steps.append(route)
            if route == "/autocomplete/json":
                self.assertEqual(
                    params,
                    {
                        "key": MOCK_API_KEY,
                        "fields": "formatted_address,name",
                        "inputtype": "textquery",
                        "types": "address",
                        "input": "Bourlottes",
                        "sessiontoken": "some_client_session_token",
                    },
                )
            if route == "/details/json":
                self.assertEqual(
                    params,
                    {
                        "key": MOCK_API_KEY,
                        "place_id": "custom_place_id",
                        "fields": "address_component,adr_address",
                        "sessiontoken": "some_client_session_token",
                    },
                )

        self.patch(
            AutoCompleteController,
            "_call_google_route",
            make_mock_google_route(on_route),
        )
        data = {
            "params": {
                "partial_address": "Bourlottes",
                "session_id": "some_client_session_token",
                "use_employees_key": True,
            }
        }
        # The route is public, but to access the feature in the backend with the
        # backend API key, one must be logged
        self.authenticate("admin", "admin")
        res = self.url_open(
            "/autocomplete/address",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        res = json.loads(res.content)
        self.assertEqual(
            res["result"]["results"],
            [
                {
                    "formatted_address": "Paris, France",
                    "google_place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
                },
                {
                    "formatted_address": "Paris, TX, USA",
                    "google_place_id": "ChIJmysnFgZYSoYRSfPTL2YJuck",
                },
                {
                    "formatted_address": "Paris, TN, USA",
                    "google_place_id": "ChIJ4zHP-Sije4gRBDEsVxunOWg",
                },
                {
                    "formatted_address": "Paris, Brant, ON, Canada",
                    "google_place_id": "ChIJsamfQbVtLIgR-X18G75Hyi0",
                },
                {
                    "formatted_address": "Paris, KY, USA",
                    "google_place_id": "ChIJsU7_xMfKQ4gReI89RJn0-RQ",
                },
            ],
        )

        data = {
            "params": {
                "address": "Ramillies",
                "google_place_id": "custom_place_id",
                "session_id": "some_client_session_token",
                "use_employees_key": True,
            }
        }
        res = self.url_open(
            "/autocomplete/address_full",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

        res = json.loads(res.content)
        self.assertEqual(
            res["result"],
            {
                "country": [13, "Australia"],
                "number": "48",
                "city": "Pyrmont",
                "street": "Pirrama Road",
                "zip": "2009",
                "state": [2, "New South Wales"],
                "formatted_street_number": "48 Pirrama Road",
            },
        )

        self.assertEqual(steps, ["/autocomplete/json", "/details/json"])

    def test_google_api_calls2(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "google_address_autocomplete.google_places_api_key", MOCK_API_KEY
        )

        def on_route(route, params):
            if route == "/details/json":
                return {
                    "result": {
                        "address_components": [
                            {
                                "long_name": "9",
                                "short_name": "9",
                                "types": ["street_number"],
                            },
                            {
                                "long_name": "rue de Bourlottes",
                                "types": ["route"],
                            },
                            {
                                "long_name": "Grand-Rosière-Hotômont",
                                "types": ["sublocality_level_1"],
                            },
                            {
                                "long_name": "Ramillies",
                                "types": ["locality"],
                            },
                        ],
                        "adr_address": "",
                    },
                    "status": "OK",
                }

        self.patch(
            AutoCompleteController,
            "_call_google_route",
            make_mock_google_route(on_route),
        )
        data = {
            "params": {
                "address": "Ramillies",
                "google_place_id": "custom_place_id",
                "session_id": "some_client_session_token",
                "use_employees_key": True,
            }
        }

        self.authenticate("admin", "admin")

        res = self.url_open(
            "/autocomplete/address_full",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        res = json.loads(res.content)["result"]
        self.assertEqual(
            res,
            {
                "city": "Ramillies",
                "formatted_street_number": "9 rue de Bourlottes",
                "number": "9",
                "street": "rue de Bourlottes",
                "street2": "Grand-Rosière-Hotômont",
            },
        )

    @mute_logger("odoo.http")
    def test_no_access(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "google_address_autocomplete.google_places_api_key", MOCK_API_KEY
        )
        self.patch(
            AutoCompleteController,
            "_call_google_route",
            make_mock_google_route(),
        )
        data = {
            "params": {
                "address": "Ramillies",
                "google_place_id": "custom_place_id",
                "session_id": "some_client_session_token",
                "use_employees_key": True
            }
        }

        res = self.url_open(
            "/autocomplete/address_full",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(res.json()["error"]["data"]["name"], "odoo.exceptions.AccessError")
