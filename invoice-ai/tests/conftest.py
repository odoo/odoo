"""Test fixtures: async client over the ASGI app + a fake Claude service.

The fake replaces the FastAPI dependency via ``app.dependency_overrides`` —
the canonical FastAPI test seam. (Patching ``app.main.get_claude_service``
by name does NOT work: ``Depends(get_claude_service)`` captured the function
object at import time, so monkeypatching the module attribute never changes
what FastAPI calls.) No Anthropic SDK, network, or API key is ever touched —
the same "mock the client" principle the Odoo suite uses.
"""

from datetime import date
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.claude import ClaudeService
from app.dependencies import get_claude_service
from app.errors import ClaudeRateLimitError
from app.main import app
from app.schemas import InvoiceLine, InvoiceExtraction


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
        transport=transport, base_url="http://test",
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
                name="Server hosting", quantity=Decimal("1.0"),
                price_unit=Decimal("850.00"),
            ),
            InvoiceLine(
                name="Setup fee", quantity=Decimal("1.0"),
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
