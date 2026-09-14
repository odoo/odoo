from unittest.mock import Mock, patch

import requests

from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import get_api_client
from odoo.addons.integration.tools.exceptions import HostNotAllowedError


@tagged("post_install", "-at_install", "integration")
class TestCredentialHostPolicy(APITransportTestCase):
    def setUp(self):
        super().setUp()
        patcher = patch("requests.Session.request")
        self.mock_request = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_request.return_value = self.create_mock_response(json_data={})

    def _sent_headers(self):
        return self.mock_request.call_args[1].get("headers", {})

    def test_absolute_url_to_a_foreign_host_is_refused_when_it_carries_the_credential(
        self,
    ):
        client = get_api_client(self.env, "test_auth_api")

        with self.assertRaises(HostNotAllowedError):
            client.get("https://collector.attacker.test/steal")

        self.mock_request.assert_not_called()

    def test_absolute_url_on_the_endpoint_host_carries_the_credential(self):
        client = get_api_client(self.env, "test_auth_api")

        client.get("https://api.example.com/v2/other")

        self.assertEqual(
            self._sent_headers()["Authorization"], "Bearer bearer_token_xyz"
        )

    def test_basic_auth_is_a_credential_too(self):
        client = get_api_client(self.env, "test_basic_auth")

        with self.assertRaises(HostNotAllowedError):
            client.get("https://elsewhere.test/")

    def test_absolute_url_without_a_credential_is_not_restricted(self):
        self.env["integration.service"].create(
            {
                "name": "Public",
                "code": "test_public_abs",
                "endpoint_url": "https://api.public.test",
                "environment": "production",
                "auth_type": "none",
            }
        )
        client = get_api_client(self.env, "test_public_abs")

        client.get("https://downloads.elsewhere.test/file.csv")

        self.mock_request.assert_called_once()

    def test_listed_host_carries_the_credential(self):
        self.service_with_auth.allowed_hosts = "uploads.example.com, files.example.com"
        client = get_api_client(self.env, "test_auth_api")

        client.get("https://files.example.com/x")

        self.assertIn("Authorization", self._sent_headers())

    def test_private_keyword_admits_private_hosts_only(self):
        self.service_with_auth.allowed_hosts = "private"
        client = get_api_client(self.env, "test_auth_api")

        client.get("https://10.0.4.21/ISAPI/System/deviceInfo")
        self.assertIn("Authorization", self._sent_headers())

        with self.assertRaises(HostNotAllowedError):
            client.get("https://8.8.8.8/ISAPI/System/deviceInfo")


@tagged("post_install", "-at_install", "integration")
class TestCredentialRedirectPolicy(APITransportTestCase):
    def _redirect(self, session, from_url, to_url, headers):
        prepared = requests.Request("GET", to_url, headers=headers).prepare()
        response = Mock()
        response.request = requests.Request("GET", from_url).prepare()
        session.rebuild_auth(prepared, response)
        return {name.lower() for name in prepared.headers}

    def test_cross_host_redirect_drops_every_credential_header(self):
        client = get_api_client(self.env, "test_auth_api")
        client.session.credential_header_names = frozenset(
            {"authorization", "x-api-key"}
        )

        remaining = self._redirect(
            client.session,
            "https://api.example.com/a",
            "https://cdn.attacker.test/b",
            {"Authorization": "Bearer s", "X-API-Key": "s", "Accept": "*/*"},
        )

        self.assertNotIn("authorization", remaining)
        self.assertNotIn("x-api-key", remaining)
        self.assertIn("accept", remaining)

    def test_same_host_redirect_keeps_the_credential_headers(self):
        client = get_api_client(self.env, "test_auth_api")
        client.session.credential_header_names = frozenset({"x-api-key"})

        remaining = self._redirect(
            client.session,
            "https://api.example.com/a",
            "https://api.example.com/b",
            {"X-API-Key": "s"},
        )

        self.assertIn("x-api-key", remaining)


@tagged("post_install", "-at_install", "integration")
class TestExplicitCredentialBinding(APITransportTestCase):
    @patch("requests.Session.request")
    def test_credential_bound_to_another_endpoint_contributes_no_secret(
        self, mock_request
    ):
        mock_request.return_value = self.create_mock_response(json_data={})

        client = get_api_client(
            self.env, "test_basic_auth", credential_id=self.credential_bearer.id
        )
        client.get("/resource")

        kwargs = mock_request.call_args[1]
        self.assertNotIn("Authorization", kwargs.get("headers", {}))
        self.assertIsNone(kwargs.get("auth"))

    @patch("requests.Session.request")
    def test_unbound_credential_contributes_no_http_auth(self, mock_request):
        mock_request.return_value = self.create_mock_response(json_data={})
        unbound = self.env["credential.credential"].create(
            {
                "name": "Unbound device login",
                "company_id": self.env.company.id,
                "category_id": self.env.ref(
                    "credential.credential_category_basic_auth"
                ).id,
                "environment": "production",
                "username": "device",
                "password": "device-pass",
            }
        )

        client = get_api_client(self.env, "test_basic_auth", credential_id=unbound.id)
        client.get("/resource")

        self.assertIsNone(mock_request.call_args[1].get("auth"))
