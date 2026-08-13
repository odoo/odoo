"""LLM service error-chain tests — HTTP client failures (v0.6 hardening).

The in-process Claude SDK mapping is gone; the addon now calls the
``invoice-ai`` service over HTTP. The clean Odoo outcomes map as:

* HTTP 503 (upstream AI down / rate limit) -> ``AIServiceUnavailable``
  (callers queue the bill for cron retry, never a permanent failure).
* HTTP 401 (bad/expired JWT) -> ``UserError`` — an Odoo-side *configuration*
  error (secret mismatch or clock skew), not a transient failure.
* HTTP 4xx (400/413/415/422) -> ``UserError`` with the service message.
* HTTP 5xx other than 503 -> ``AIServiceUnavailable``.
* ``requests.Timeout`` -> retried once, then ``UserError``.
* Circuit breaker: 5 consecutive failures trip it open; a call then fails
  immediately without touching the network (see test_llm_service.py for the
  breaker matrix — the focus here is the error mapping itself).
"""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.invoice_agent.models import llm_service as svc


class _FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body if body is not None else {}

    def json(self):
        return self._body


def _error_body(code, message, retry_after=None):
    body = {"error": {"code": code, "message": message}}
    if retry_after is not None:
        body["error"]["retry_after_seconds"] = retry_after
    return body


@tagged("post_install", "-at_install")
class TestLlmHttpErrorChain(TransactionCase):

    def setUp(self):
        super().setUp()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("invoice_agent.llm_service_url", "http://invoice-ai:8000")
        icp.set_param("invoice_agent.jwt_secret", "test-shared-secret")
        self.service = self.env["invoice.llm.service"]
        svc._circuit["consecutive_failures"] = 0
        svc._circuit["open_until"] = 0.0

    def tearDown(self):
        svc._circuit["consecutive_failures"] = 0
        svc._circuit["open_until"] = 0.0
        super().tearDown()

    def test_503_maps_to_aiservice_unavailable(self):
        with patch(
            "requests.post",
            return_value=_FakeResponse(503, _error_body("E5031", "upstream")),
        ):
            with self.assertRaises(svc.AIServiceUnavailable):
                self.service.extract_invoice("invoice text")

    def test_503_carries_retry_after_hint(self):
        with patch(
            "requests.post",
            return_value=_FakeResponse(
                503,
                _error_body("E5031", "rate limited", retry_after=17),
            ),
        ):
            with self.assertRaises(svc.AIServiceUnavailable) as ctx:
                self.service.extract_invoice("invoice text")
        self.assertIn("17", ctx.exception.args[0])

    def test_401_maps_to_user_error(self):
        with patch(
            "requests.post",
            return_value=_FakeResponse(401, _error_body("E4011", "bad token")),
        ):
            with self.assertRaises(UserError) as ctx:
                self.service.extract_invoice("invoice text")
        self.assertIn("401", ctx.exception.args[0])

    def test_400_maps_to_user_error(self):
        with patch(
            "requests.post",
            return_value=_FakeResponse(400, _error_body("E4001", "bad request")),
        ):
            with self.assertRaises(UserError) as ctx:
                self.service.extract_invoice("invoice text")
        self.assertIn("E4001", ctx.exception.args[0])

    def test_422_maps_to_user_error(self):
        with patch(
            "requests.post",
            return_value=_FakeResponse(422, _error_body("E4221", "schema drift")),
        ):
            with self.assertRaises(UserError) as ctx:
                self.service.extract_invoice("invoice text")
        self.assertIn("E4221", ctx.exception.args[0])

    def test_500_maps_to_aiservice_unavailable(self):
        with patch(
            "requests.post",
            return_value=_FakeResponse(502, _error_body("E5031", "bad gateway")),
        ):
            with self.assertRaises(svc.AIServiceUnavailable):
                self.service.extract_invoice("invoice text")

    def test_timeout_retries_then_user_error(self):
        with patch(
            "requests.post",
            side_effect=svc.requests.Timeout("drop"),
        ) as mock_post:
            with self.assertRaises(UserError) as ctx:
                self.service.extract_invoice("invoice text")
        self.assertIn("timed out", ctx.exception.args[0])
        # The brief: a timeout is retried once, then raised.
        self.assertEqual(mock_post.call_count, svc.TIMEOUT_RETRIES + 1)

    def test_missing_url_raises_user_error(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "invoice_agent.llm_service_url", ""
        )
        with self.assertRaises(UserError) as ctx:
            self.service.extract_invoice("invoice text")
        self.assertIn("URL", ctx.exception.args[0])

    def test_missing_secret_raises_user_error(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "invoice_agent.jwt_secret", ""
        )
        with self.assertRaises(UserError) as ctx:
            self.service.extract_invoice("invoice text")
        self.assertIn("JWT", ctx.exception.args[0])
