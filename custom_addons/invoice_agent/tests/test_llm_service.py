"""LLM service — HTTP client tests for the invoice-ai FastAPI service.

The in-process Claude call is gone (ADR-003); ``extract_invoice`` is now an
HTTP call to the standalone service. This suite replaces the old
Anthropic-mocking tests with contract tests that drive the addon's real
client code against a stubbed ``requests.post``:

* JWT claims are correct (aud=invoice-ai, 60 s expiry, iss/sub set) and the
  Authorization header carries one;
* HTTP 200 → schema-validated ``InvoiceExtraction`` (parsed/usage/model);
* HTTP 503 → ``AIServiceUnavailable`` (callers route to cron retry);
* HTTP 401 → ``UserError`` (config error — secret mismatch / clock skew);
* ``requests.Timeout`` → retried once, then ``UserError``;
* the circuit breaker trips after 5 consecutive failures and stops
  hammering the dead service.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from odoo.addons.invoice_agent.models import llm_service as svc

from odoo.addons.invoice_agent.models.invoice_extraction import (
    _PYDANTIC_AVAILABLE,
)


def _fake_response(status_code=200, body=None):
    class FakeResponse:
        def __init__(self, payload, status_code):
            self._payload = payload
            self.status_code = status_code

        def json(self):
            return self._payload

    return FakeResponse(body if body is not None else {}, status_code)


def _happy_body():
    return {
        "extraction": {
            "vendor_name": "ACME Supplies LLC",
            "vendor_vat": "US123456789",
            "invoice_date": "2026-07-01",
            "due_date": "2026-07-31",
            "currency": "USD",
            "subtotal": 1350.0,
            "tax_total": 0.0,
            "amount_total": 1350.0,
            "lines": [
                {"name": "Server hosting", "quantity": 1.0, "price_unit": 850.0},
                {"name": "Setup fee", "quantity": 1.0, "price_unit": 500.0},
            ],
        },
        "usage": {
            "input_tokens": 4000,
            "cache_creation_input_tokens": 4500,
            "cache_read_input_tokens": 4400,
            "output_tokens": 500,
        },
        "model": "claude-opus-4-8",
    }


@tagged("post_install", "-at_install")
class TestLlmServiceHttp(TransactionCase):

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

    # ------------------------------------------------------------------
    # JWT minting
    # ------------------------------------------------------------------
    def test_mint_jwt_claims(self):
        token = svc.mint_jwt("test-shared-secret")
        claims = jwt.decode(
            token,
            "test-shared-secret",
            algorithms=["HS256"],
            audience="invoice-ai",
        )
        self.assertEqual(claims["iss"], "odoo.invoice-agent")
        self.assertEqual(claims["sub"], "invoice.llm.service")
        self.assertEqual(claims["aud"], "invoice-ai")
        # 60-second expiry: iat → exp is exactly JWT_TTL_SECONDS.
        issued = datetime.fromtimestamp(claims["iat"], tz=timezone.utc)
        expires = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        self.assertAlmostEqual(
            (expires - issued).total_seconds(),
            svc.JWT_TTL_SECONDS,
            delta=2,
        )

    def test_expired_token_rejected_by_service_verifier(self):
        """A token minted 120s ago fails the service's verifier (leeway 10s)."""
        from jwt.exceptions import ExpiredSignatureError

        token = svc.mint_jwt("test-shared-secret")
        claims = jwt.decode(
            token,
            "test-shared-secret",
            algorithms=["HS256"],
            audience="invoice-ai",
            options={"verify_exp": False},
        )
        past = datetime.now(timezone.utc) - timedelta(seconds=120)
        claims["iat"] = past
        claims["exp"] = past + timedelta(seconds=10)
        expired = jwt.encode(claims, "test-shared-secret", algorithm="HS256")
        with self.assertRaises(ExpiredSignatureError):
            jwt.decode(
                expired,
                "test-shared-secret",
                algorithms=["HS256"],
                audience="invoice-ai",
                leeway=10,
            )

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------
    def test_extract_invoice_success(self):
        if not _PYDANTIC_AVAILABLE:
            self.skipTest("pydantic unavailable in this image")

        captured = {}

        def _fake_post(url, files=None, data=None, headers=None, timeout=None):
            captured["url"] = url
            captured["files"] = files
            captured["data"] = data
            captured["headers"] = headers
            captured["timeout"] = timeout
            return _fake_response(200, _happy_body())

        with patch("requests.post", side_effect=_fake_post):
            result = self.service.extract_invoice("ACME SUPPLIES LLC")

        # URL contract: base_url + /v1/extract, 90s timeout.
        self.assertEqual(captured["url"], "http://invoice-ai:8000/v1/extract")
        self.assertEqual(captured["timeout"], svc.EXTRACT_TIMEOUT_SECONDS)
        # Multipart form: text file part + effort form field.
        self.assertEqual(captured["files"], {"text": (None, "ACME SUPPLIES LLC")})
        self.assertEqual(captured["data"], {"effort": "normal"})
        # Authorization header carries a valid JWT for the shared secret.
        bearer = captured["headers"]["Authorization"]
        self.assertTrue(bearer.startswith("Bearer "))
        claims = jwt.decode(
            bearer[len("Bearer "):],
            "test-shared-secret",
            algorithms=["HS256"],
            audience="invoice-ai",
        )
        self.assertEqual(claims["aud"], "invoice-ai")

        # Response contract: same dict shape the callers already consume.
        self.assertEqual(result["parsed"].vendor_name, "ACME Supplies LLC")
        self.assertEqual(result["parsed"].currency, "USD")
        self.assertEqual(float(result["parsed"].amount_total), 1350.0)
        self.assertEqual(result["model"], "claude-opus-4-8")
        self.assertEqual(result["usage"]["output_tokens"], 500)

    # ------------------------------------------------------------------
    # Failure mapping
    # ------------------------------------------------------------------
    def test_503_raises_aiservice_unavailable(self):
        body = {
            "error": {
                "code": "E5031",
                "message": "upstream",
                "retry_after_seconds": 12,
            },
        }
        with patch("requests.post", return_value=_fake_response(503, body)):
            with self.assertRaises(svc.AIServiceUnavailable):
                self.service.extract_invoice("ACME")

    def test_401_raises_user_error(self):
        body = {"error": {"code": "E4011", "message": "Invalid or expired token"}}
        with patch("requests.post", return_value=_fake_response(401, body)):
            with self.assertRaises(UserError) as ctx:
                self.service.extract_invoice("ACME")
        self.assertIn("401", ctx.exception.args[0])

    def test_400_raises_user_error_with_service_message(self):
        body = {
            "error": {
                "code": "E4001",
                "message": "Provide either 'file' or 'text'.",
            },
        }
        with patch("requests.post", return_value=_fake_response(400, body)):
            with self.assertRaises(UserError) as ctx:
                self.service.extract_invoice("ACME")
        self.assertIn("E4001", ctx.exception.args[0])

    def test_timeout_retried_once_then_user_error(self):
        with patch(
            "requests.post",
            side_effect=svc.requests.Timeout("timed out"),
        ) as mock_post:
            with self.assertRaises(UserError) as ctx:
                self.service.extract_invoice("ACME")
        self.assertEqual(mock_post.call_count, svc.TIMEOUT_RETRIES + 1)
        self.assertIn("timed out", ctx.exception.args[0])

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------
    def test_circuit_breaker_stops_hammering_dead_service(self):
        body = {"error": {"code": "E5031", "message": "upstream"}}
        with patch("requests.post", return_value=_fake_response(503, body)):
            for _ in range(svc.CIRCUIT_FAILURE_THRESHOLD):
                with self.assertRaises(svc.AIServiceUnavailable):
                    self.service.extract_invoice("ACME")

        # The circuit is open: the next call must fail immediately without
        # touching the network.
        with patch("requests.post") as mock_post:
            with self.assertRaises(svc.AIServiceUnavailable):
                self.service.extract_invoice("ACME")
            mock_post.assert_not_called()

    def test_circuit_breaker_resets_after_success(self):
        body = {"error": {"code": "E5031", "message": "upstream"}}
        with patch("requests.post", return_value=_fake_response(503, body)):
            for _ in range(svc.CIRCUIT_FAILURE_THRESHOLD):
                with self.assertRaises(svc.AIServiceUnavailable):
                    self.service.extract_invoice("ACME")

        self.service.reset_circuit_breaker_for_tests()

        if not _PYDANTIC_AVAILABLE:
            self.skipTest("pydantic unavailable in this image")
        with patch("requests.post", return_value=_fake_response(200, _happy_body())):
            result = self.service.extract_invoice("ACME")
        self.assertEqual(result["parsed"].vendor_name, "ACME Supplies LLC")
