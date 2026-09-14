"""Tests for the IAP tools: email domain search and the JSON-RPC contract."""

from unittest.mock import MagicMock, patch

import requests as requests_lib

from odoo import exceptions
from odoo.libs.guarded_http import GuardedSession
from odoo.tests import TransactionCase, tagged

from odoo.addons.iap.tools.iap_tools import (
    InsufficientCreditError,
    iap_get_endpoint,
    iap_jsonrpc,
    mail_prepare_for_domain_search,
)

TOOLS = "odoo.addons.iap.tools.iap_tools"


@tagged("post_install", "-at_install")
class TestMailDomainSearch(TransactionCase):
    def test_generic_provider_keeps_full_email(self):
        """Blacklisted generic domains (gmail...) search by full address."""
        self.assertEqual(
            mail_prepare_for_domain_search("raoul@gmail.com"), "raoul@gmail.com"
        )

    def test_company_domain_reduced_to_domain(self):
        """Company domains reduce to '@domain' for the search."""
        self.assertEqual(
            mail_prepare_for_domain_search("raoul@mydomain.com"), "@mydomain.com"
        )

    def test_empty_email_returns_false(self):
        """No email means no search term (boundary)."""
        self.assertFalse(mail_prepare_for_domain_search(False))

    def test_short_email_skipped_with_min_length(self):
        """Emails under the minimal length are treated as fake (boundary)."""
        self.assertFalse(mail_prepare_for_domain_search("a@b.c", min_email_length=10))

    def test_endpoint_param_overrides_default(self):
        """The iap.endpoint parameter overrides the default endpoint."""
        self.env["ir.config_parameter"].sudo().set_param(
            "iap.endpoint", "https://iap.test.example.com"
        )
        self.assertEqual(iap_get_endpoint(self.env), "https://iap.test.example.com")


@tagged("post_install", "-at_install")
class TestIapJsonrpcContract(TransactionCase):
    """The in-test guard is lifted with requests mocked: no real call can occur."""

    def _call(self, response=None, side_effect=None):
        mock_response = MagicMock()
        mock_response.json.return_value = response or {}
        mock_response.elapsed.total_seconds.return_value = 0.0
        with (
            patch(f"{TOOLS}.modules.module.current_test", False),
            patch.object(
                GuardedSession,
                "request",
                return_value=mock_response,
                side_effect=side_effect,
            ),
        ):
            return iap_jsonrpc("https://iap.mock/rpc", params={"x": 1}, env=self.env)

    def test_success_unwraps_result(self):
        """A successful JSON-RPC reply returns the bare result."""
        self.assertEqual(self._call({"result": {"ok": True}}), {"ok": True})

    def test_insufficient_credit_maps_to_typed_error(self):
        """The credit error name maps to InsufficientCreditError with data."""
        payload = {
            "error": {
                "data": {
                    "name": "odoo.addons.iap.InsufficientCreditError",
                    "message": "no credits",
                }
            }
        }
        with self.assertRaises(InsufficientCreditError) as capture:
            self._call(payload)
        self.assertEqual(capture.exception.data["message"], "no credits")

    def test_other_server_error_maps_to_access_error(self):
        """Any other server-side error surfaces as an AccessError."""
        payload = {"error": {"data": {"name": "whatever.Error", "message": "boom"}}}
        with self.assertRaises(exceptions.AccessError):
            self._call(payload)

    def test_error_without_name_maps_to_access_error(self):
        """An error.data with no 'name' key surfaces as an AccessError
        instead of crashing with a raw AttributeError."""
        payload = {"error": {"data": {"message": "boom"}}}
        with self.assertRaises(exceptions.AccessError):
            self._call(payload)

    def test_error_without_data_maps_to_access_error(self):
        """An error with no 'data' key at all surfaces as an AccessError
        instead of crashing with a raw KeyError."""
        payload = {"error": {}}
        with self.assertRaises(exceptions.AccessError):
            self._call(payload)

    def test_timeout_maps_to_access_error(self):
        """A transport timeout surfaces as an AccessError (boundary)."""
        with self.assertRaises(exceptions.AccessError):
            self._call(side_effect=requests_lib.exceptions.Timeout())

    def test_guard_blocks_real_calls_in_tests(self):
        """Without the lifted guard, IAP calls are refused during tests."""
        with self.assertRaises(exceptions.AccessError):
            iap_jsonrpc("https://iap.real/rpc", env=self.env)
