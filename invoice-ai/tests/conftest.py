"""Test fixtures: async client over the ASGI app + a fake Claude service.

The fake replaces the FastAPI dependency via ``app.dependency_overrides`` —
the canonical FastAPI test seam. (Patching ``app.main.get_claude_service``
by name does NOT work: ``Depends(get_claude_service)`` captured the function
object at import time, so monkeypatching the module attribute never changes
what FastAPI calls.) No Anthropic SDK, network, or API key is ever touched —
the same "mock the client" principle the Odoo suite uses.

JWT auth: ``/v1/extract`` now sits behind ``Depends(require_token)``. The
``jwt_secret`` autouse fixture sets ``settings.jwt_secret`` per test so
authenticated requests succeed and negative auth tests can mint their own
(expired/wrong-audience) tokens.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import jwt
import pytest
from app.claude import ClaudeService
from app.config import settings
from app.dependencies import get_claude_service
from app.main import app
from app.schemas import InvoiceExtraction, InvoiceLine
from httpx import ASGITransport, AsyncClient

TEST_JWT_SECRET = "test-shared-secret-not-for-production"


class FakeClaude(ClaudeService):
    """Configurable stand-in for the real Anthropic-backed service."""

    result: dict | None = None
    error: Exception | None = None
    last_args: dict = {}

    def __init__(self):
        # Do not touch the SDK: skip ClaudeService.__init__.
        object.__init__(self)

    async def extract(self, text: str, effort: str = "normal"):
        self.last_args = {"text": text, "effort": effort}
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture(autouse=True)
def jwt_settings(monkeypatch):
    """Set a known JWT secret + audience for every test.

    Autouse so the pre-auth-era tests keep working unchanged once they send
    the ``auth_headers`` fixture, and so negative auth tests can rely on a
    deterministic secret.
    """
    monkeypatch.setattr(settings, "jwt_secret", TEST_JWT_SECRET)
    monkeypatch.setattr(settings, "jwt_audience", "invoice-ai")
    yield


def mint_token(
    secret: str = TEST_JWT_SECRET,
    *,
    audience: str = "invoice-ai",
    issuer: str = "odoo.invoice-agent",
    subject: str = "invoice.llm.service",
    expires_in: timedelta = timedelta(seconds=60),
    now: datetime | None = None,
) -> str:
    """Mint a JWT exactly like the Odoo side does (60 s expiry, HS256).

    The claims mirror ``invoice_agent.models.llm_service._mint_jwt``: iss,
    aud, sub, iat, exp. ``now`` lets tests mint an *already-expired* token
    by passing ``now=datetime.now(timezone.utc) - timedelta(seconds=120)``.
    """
    now = now or datetime.now(UTC)
    return jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "sub": subject,
            "iat": now,
            "exp": now + expires_in,
        },
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """A valid Authorization header for the happy-path tests."""
    return {"Authorization": f"Bearer {mint_token()}"}


@pytest.fixture
def fake_claude():
    fake = FakeClaude()
    app.dependency_overrides[get_claude_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_claude_service, None)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client


def make_result(vendor_name="ACME SUPPLIES LLC") -> dict:
    """A schema-validated extraction result, JSON-serializable."""
    extraction = InvoiceExtraction(
        vendor_name=vendor_name,
        vendor_vat="US123456789",
        invoice_date=date(2026, 7, 1),
        due_date=date(2026, 7, 31),
        currency="USD",
        subtotal=Decimal("1350.00"),
        tax_total=Decimal("0.00"),
        amount_total=Decimal("1350.00"),
        lines=[
            InvoiceLine(
                name="Server hosting",
                quantity=Decimal("1.0"),
                price_unit=Decimal("850.00"),
            ),
            InvoiceLine(
                name="Setup fee",
                quantity=Decimal("1.0"),
                price_unit=Decimal("500.00"),
            ),
        ],
    )
    return {
        "parsed": extraction,
        "usage": {
            "input_tokens": 4000,
            "cache_creation_input_tokens": 4500,
            "cache_read_input_tokens": 4400,
            "output_tokens": 500,
        },
        "model": "claude-opus-4-8",
    }


@pytest.fixture
def default_result():
    return make_result()
