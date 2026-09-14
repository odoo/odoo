from unittest.mock import patch

import requests

from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.integration.tools import get_api_client
from odoo.addons.integration.tools.exceptions import (
    AuthenticationError,
    ClientError,
    CommError,
    CommTimeoutError,
    RateLimitError,
    ServerError,
)


@tagged("post_install", "-at_install")
class TestExceptionCarriesStatus(TransactionCase):
    def test_every_class_defaults_the_status_to_none(self):
        for cls in (
            CommError,
            AuthenticationError,
            RateLimitError,
            CommTimeoutError,
            ClientError,
            ServerError,
        ):
            with self.subTest(cls=cls.__name__):
                error = cls("boom") if cls is CommError else cls()
                self.assertIsNone(error.status_code)

    def test_the_status_survives_the_constructor(self):
        self.assertEqual(ClientError("not found", 404).status_code, 404)


@tagged("post_install", "-at_install")
class TestClientPopulatesStatus(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.endpoint = cls.env["integration.service"].create(
            {
                "name": "status probe",
                "code": "status_probe",
                "endpoint_url": "https://example.invalid/api",
                "auth_type": "none",
                "retry_enabled": False,
            }
        )

    def _raise_http(self, status):
        response = requests.Response()
        response.status_code = status
        response._content = b'{"message": "nope"}'
        response.url = "https://example.invalid/api/thing"
        return requests.exceptions.HTTPError(response=response)

    def _get_with_status(self, status):
        client = get_api_client(self.env, "status_probe")
        with patch.object(
            client.session, "request", side_effect=self._raise_http(status)
        ):
            with self.assertRaises(CommError) as caught:
                client.get("/thing")
        return caught.exception

    @mute_logger("odoo.addons.integration.tools.api_client")
    def test_a_404_is_distinguishable_from_a_422(self):
        not_found = self._get_with_status(404)
        unprocessable = self._get_with_status(422)

        self.assertIsInstance(not_found, ClientError)
        self.assertIsInstance(unprocessable, ClientError)
        self.assertEqual(
            type(not_found),
            type(unprocessable),
            "the band is the same by design -- the status is what separates them",
        )
        self.assertEqual(not_found.status_code, 404)
        self.assertEqual(unprocessable.status_code, 422)

    @mute_logger("odoo.addons.integration.tools.api_client")
    def test_each_band_carries_its_own_status(self):
        for status, cls in (
            (401, AuthenticationError),
            (429, RateLimitError),
            (403, ClientError),
            (503, ServerError),
        ):
            with self.subTest(status=status):
                error = self._get_with_status(status)
                self.assertIsInstance(error, cls)
                self.assertEqual(error.status_code, status)

    @mute_logger("odoo.addons.integration.tools.api_client")
    def test_a_timeout_has_no_status_to_carry(self):
        client = get_api_client(self.env, "status_probe")
        with patch.object(
            client.session,
            "request",
            side_effect=requests.exceptions.ReadTimeout("slow"),
        ):
            with self.assertRaises(CommTimeoutError) as caught:
                client.get("/thing")
        self.assertIsNone(caught.exception.status_code)
