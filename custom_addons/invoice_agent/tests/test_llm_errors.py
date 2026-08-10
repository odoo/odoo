"""LLM service error-chain tests (v0.6 hardening).

Maps the SDK exception hierarchy (most-specific-first) to distinct,
accountant-readable UserErrors: NotFoundError -> "call IT", RateLimitError ->
"retry after Ns", APIStatusError -> "call IT with status", APIConnectionError
-> "check internet".
"""

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.invoice_agent.models import llm_service as svc

from anthropic import (
    APIConnectionError,
    APIStatusError,
    NotFoundError,
    RateLimitError,
)


def _fake_response(status_code=200, headers=None):
    """httpx.Response-compatible fake: SDK constructors read .request."""
    request = type("Req", (), {"method": "POST", "url": "http://x"})()
    return type("Resp", (), {
        "status_code": status_code,
        "headers": headers or {},
        "request": request,
    })()


@tagged("post_install", "-at_install")
class TestLlmErrorChain(TransactionCase):

    def setUp(self):
        super().setUp()
        self.env["ir.config_parameter"].sudo().set_param(
            "invoice_agent.anthropic_api_key", "sk-test-key-123"
        )
        self.service = self.env["invoice.llm.service"]

    def _map(self, exc):
        return svc.InvoiceLlmService._map_sdk_error(self.service, exc)

    def test_rate_limit_reads_retry_after(self):
        exc = RateLimitError("rate limited", response=_fake_response(429, {"Retry-After": "37"}), body=None)
        mapped = self._map(exc)
        self.assertIsInstance(mapped, UserError)
        self.assertIn("37", mapped.args[0])
        self.assertIn("try again", mapped.args[0])

    def test_rate_limit_without_retry_after(self):
        exc = RateLimitError("rate limited", response=_fake_response(429), body=None)
        mapped = self._map(exc)
        self.assertIn("rate-limiting", mapped.args[0])

    def test_not_found_says_call_it(self):
        exc = NotFoundError("no model", response=_fake_response(404), body=None)
        mapped = self._map(exc)
        self.assertIn("contact IT", mapped.args[0])

    def test_status_error_includes_http_code(self):
        exc = APIStatusError("boom", response=_fake_response(500), body=None)
        mapped = self._map(exc)
        self.assertIn("500", mapped.args[0])

    def test_connection_error_says_try_again(self):
        exc = APIConnectionError(request=_fake_response(0).request)
        mapped = self._map(exc)
        self.assertIn("Could not reach", mapped.args[0])
