"""
locustfile.py — Load test for the full invoice agent pipeline.

Usage:
    # Smoke test (5 concurrent users):
    locust --headless -u 5 -r 1 --run-time 2m

    # Ramp to breaking point (100 users, spawn 2/sec):
    locust --headless -u 100 -r 2 --run-time 30m

    # With web UI (open http://localhost:8089):
    locust

Environment variables:
    LOCUST_INVOICE_AI_URL  — base URL of invoice-ai (default: http://localhost:8100)
    LOCUST_ODOO_URL        — base URL of Odoo (default: http://localhost:8069)
    LOCUST_JWT_SECRET      — shared JWT secret for signing
    LOCUST_PDF_DIR         — directory containing test invoice PDFs
    LOCUST_DATABASE_URL    — for Odoo auth (db name)
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from locust import HttpUser, between, events, task
from locust.load_test_shape import LoadTestShape


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INVOICE_AI_URL = os.getenv("LOCUST_INVOICE_AI_URL", "http://localhost:8100")
ODOO_URL = os.getenv("LOCUST_ODOO_URL", "http://localhost:8069")
JWT_SECRET = os.getenv("LOCUST_JWT_SECRET", "")
PDF_DIR = Path(os.getenv("LOCUST_PDF_DIR", "invoice-ai/tests/fixtures"))
EXTRACTION_TIMEOUT = int(os.getenv("LOCUST_EXTRACTION_TIMEOUT", "60"))  # seconds


# ---------------------------------------------------------------------------
# Helper: generate a JWT for invoice-ai auth
# ---------------------------------------------------------------------------
def _mint_jwt() -> str:
    """Mint a short-lived JWT matching invoice-ai/app/auth.py."""
    try:
        import jwt as pyjwt
    except ImportError:
        import PyJWT as pyjwt  # type: ignore[no-redef]

    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": "load-test",
            "aud": "invoice-ai",
            "iat": now,
            "exp": now + 300,  # 5 minutes
        },
        JWT_SECRET,
        algorithm="HS256",
    )


# ---------------------------------------------------------------------------
# Test fixtures: collect PDF files at test start
# ---------------------------------------------------------------------------
_PDF_FILES: list[Path] = []


@events.test_start.add_listener
def on_test_start(environment, **kwargs):  # type: ignore[no-untyped-def]
    """Collect test PDFs at the start of the test."""
    global _PDF_FILES
    if PDF_DIR.exists():
        _PDF_FILES = sorted(
            list(PDF_DIR.glob("*.pdf")) + list(PDF_DIR.glob("*.png"))
        )
    if not _PDF_FILES:
        print(
            f"WARNING: No PDF/PNG fixtures found in {PDF_DIR}. "
            "Create test invoices or set LOCUST_PDF_DIR."
        )


# ---------------------------------------------------------------------------
# Staged load shape — ramp 10 → 25 → 50 → 100 users
# ---------------------------------------------------------------------------
class StagedLoadShape(LoadTestShape):
    """Staged ramp: warm up → moderate → heavy → stress → spike → hold.

    Use with: locust -f locustfile.py --headless
    The stages define target user count + spawn rate at each time boundary.
    """

    stages = [
        {"duration": 120, "users": 10, "spawn_rate": 1},   # 0-2 min: warm up
        {"duration": 300, "users": 25, "spawn_rate": 2},   # 2-5 min: moderate
        {"duration": 600, "users": 50, "spawn_rate": 3},   # 5-10 min: heavy
        {"duration": 900, "users": 75, "spawn_rate": 3},   # 10-15 min: stress
        {"duration": 1200, "users": 100, "spawn_rate": 4}, # 15-20 min: spike
        {"duration": 1800, "users": 100, "spawn_rate": 0}, # 20-30 min: hold
    ]

    def tick(self) -> tuple[int, int] | None:
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None  # stop


# ---------------------------------------------------------------------------
# InvoiceExtractorUser — tests POST /v1/extract directly
# ---------------------------------------------------------------------------
class InvoiceExtractorUser(HttpUser):
    """Simulates a client sending invoice PDFs to the extraction service.

    Each user:
    1. Picks a PDF from the fixture directory (deterministic by user count).
    2. POSTs it to /v1/extract with a fresh JWT.
    3. Validates the response contains extraction data.
    4. Waits 1-5 seconds between requests.
    """

    wait_time = between(1, 5)
    host = INVOICE_AI_URL

    def on_start(self) -> None:
        """Set up auth headers once per user."""
        self.jwt = _mint_jwt()

    @task(10)
    def extract_invoice(self) -> None:
        """POST a PDF to /v1/extract — the core extraction path."""
        if not _PDF_FILES:
            return

        # Deterministic selection: same invoice text → realistic cache hit
        idx = self.environment.runner.user_count % len(_PDF_FILES)  # type: ignore[union-attr]
        pdf_path = _PDF_FILES[idx]

        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            with self.client.post(
                "/v1/extract",
                files=files,
                headers={"Authorization": f"Bearer {self.jwt}"},
                name="/v1/extract",
                catch_response=True,
            ) as response:
                if response.status_code == 200:
                    body = response.json()
                    if "extraction" in body:
                        response.success()
                    else:
                        response.failure("Response missing 'extraction' key")
                elif response.status_code == 429:
                    response.failure(f"Rate limited: {response.text}")
                else:
                    response.failure(
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )

    @task(2)
    def health_check(self) -> None:
        """GET /healthz — lightweight liveness probe."""
        self.client.get("/healthz", name="/healthz")

    @task(1)
    def embed_endpoint(self) -> None:
        """POST /v1/embed — test the embedding path under load."""
        payload = {
            "texts": [
                "Vendor: Acme Corp | Date: 2026-01-15 | Total: 1500.00 USD | "
                "Lines: Office supplies [610000] x10 = 1500.00"
            ]
        }
        self.client.post(
            "/v1/embed",
            json=payload,
            headers={"Authorization": f"Bearer {self.jwt}"},
            name="/v1/embed",
        )


# ---------------------------------------------------------------------------
# FullPipelineUser — tests the AMQP path through Odoo
# ---------------------------------------------------------------------------
class FullPipelineUser(HttpUser):
    """Simulates the full end-to-end pipeline through Odoo.

    Each user:
    1. Logs into Odoo (JSON-RPC auth).
    2. Creates a draft vendor bill.
    3. Triggers extraction (AMQP job).
    4. Polls until ai_extraction_status changes.
    5. Records the end-to-end latency.
    """

    wait_time = between(2, 8)
    host = ODOO_URL

    def on_start(self) -> None:
        """Authenticate with Odoo and store session."""
        self.session_id: str | None = None
        self._login_odoo()

    def _login_odoo(self) -> None:
        """Authenticate via Odoo JSON-RPC."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "authenticate",
                "args": [
                    os.getenv("LOCUST_ODOO_DB", "odoo"),
                    os.getenv("LOCUST_ODOO_USER", "admin"),
                    os.getenv("LOCUST_ODOO_PASSWORD", "admin"),
                    {},
                ],
            },
        }
        resp = self.client.post("/jsonrpc", json=payload, name="/jsonrpc/auth")
        if resp.ok:
            self.session_id = resp.json().get("result")

    def _jsonrpc_call(self, model: str, method: str, args: list) -> dict | None:
        """Execute an Odoo JSON-RPC method call."""
        if not self.session_id:
            return None
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    os.getenv("LOCUST_ODOO_DB", "odoo"),
                    self.session_id,
                    os.getenv("LOCUST_ODOO_PASSWORD", "admin"),
                    model,
                    method,
                    args,
                ],
            },
        }
        resp = self.client.post(
            "/jsonrpc", json=payload, name=f"/jsonrpc/{model}.{method}",
        )
        if resp.ok:
            return resp.json().get("result")
        return None

    @task(5)
    def full_extraction_pipeline(self) -> None:
        """End-to-end: create bill -> trigger extraction -> poll result."""
        if not self.session_id:
            self._login_odoo()
            if not self.session_id:
                return

        start_time = time.monotonic()

        # Step 1: Create a draft vendor bill
        move_id = self._jsonrpc_call(
            "account.move", "create", [{"move_type": "in_invoice"}],
        )
        if not move_id:
            return

        # Step 2: Trigger extraction
        self._jsonrpc_call(
            "account.move", "action_request_ai_extraction", [move_id],
        )

        # Step 3: Poll until extraction completes or timeout
        deadline = start_time + EXTRACTION_TIMEOUT
        while time.monotonic() < deadline:
            time.sleep(2)

            result = self._jsonrpc_call(
                "account.move",
                "read",
                [move_id, ["ai_extraction_status", "confidence_score"]],
            )
            if result and len(result) > 0:
                status = result[0].get("ai_extraction_status")
                if status in ("extracted", "validated", "failed"):
                    elapsed = time.monotonic() - start_time
                    self.environment.events.request.fire(
                        request_type="pipeline",
                        name="full_extraction",
                        response_time=elapsed * 1000,  # ms
                        response_length=0,
                        exception=None,
                    )
                    return

        # Timeout
        self.environment.events.request.fire(
            request_type="pipeline",
            name="full_extraction",
            response_time=EXTRACTION_TIMEOUT * 1000,
            response_length=0,
            exception=TimeoutError(
                f"Extraction did not complete in {EXTRACTION_TIMEOUT}s"
            ),
        )
