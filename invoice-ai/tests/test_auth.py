"""JWT auth contract tests for ``Depends(require_token)``.

Covers the brief's requirement: *any unauthenticated request to
``/v1/extract`` is rejected with 401*. The positive path (valid token) is
already exercised by the happy-path test in ``test_extract.py`` with the
``auth_headers`` fixture; this module covers the failure matrix:

* missing Authorization header            -> 401
* non-Bearer scheme                       -> 401
* garbage token                           -> 401
* valid signature, wrong audience         -> 401
* token signed with the wrong secret      -> 401
* expired token                           -> 401
* /healthz stays open (no auth required)  -> 200
* shared secret not configured            -> 401 (fails closed)
"""

from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings

from .conftest import mint_token

EXPIRED_NOW = datetime.now(UTC) - timedelta(seconds=120)


@pytest.mark.anyio
async def test_extract_without_token_returns_401(client, fake_claude):
    response = await client.post(
        "/v1/extract",
        data={"text": "ACME SUPPLIES LLC\nTOTAL USD 1,350.00"},
    )
    # FastAPI's default HTTPException handler returns {"detail": ...}; the
    # client contract only requires the 401 status (the Odoo side maps any
    # 401 to "configuration error").
    assert response.status_code == 401


@pytest.mark.anyio
async def test_extract_with_non_bearer_scheme_returns_401(client, fake_claude):
    response = await client.post(
        "/v1/extract",
        headers={"Authorization": f"Token {mint_token()}"},
        data={"text": "ACME SUPPLIES LLC"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_extract_with_garbage_token_returns_401(client, fake_claude):
    response = await client.post(
        "/v1/extract",
        headers={"Authorization": "Bearer not.a.jwt"},
        data={"text": "ACME SUPPLIES LLC"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_extract_with_wrong_audience_returns_401(client, fake_claude):
    token = mint_token(audience="odoo-other-service")
    response = await client.post(
        "/v1/extract",
        headers={"Authorization": f"Bearer {token}"},
        data={"text": "ACME SUPPLIES LLC"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_extract_with_wrong_secret_returns_401(client, fake_claude):
    token = mint_token(secret="attacker-guessed-secret")
    response = await client.post(
        "/v1/extract",
        headers={"Authorization": f"Bearer {token}"},
        data={"text": "ACME SUPPLIES LLC"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_extract_with_expired_token_returns_401(client, fake_claude):
    token = mint_token(now=EXPIRED_NOW)
    response = await client.post(
        "/v1/extract",
        headers={"Authorization": f"Bearer {token}"},
        data={"text": "ACME SUPPLIES LLC"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_healthz_never_requires_a_token(client):
    """The compose healthcheck curls /healthz without any credentials."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.anyio
async def test_extract_fails_closed_when_secret_not_configured(
    client,
    fake_claude,
    monkeypatch,
):
    """A service without INVOICE_AI_JWT_SECRET refuses every request, even
    ones signed with a known secret — never silently accepts."""
    monkeypatch.setattr(settings, "jwt_secret", "")
    token = mint_token()
    response = await client.post(
        "/v1/extract",
        headers={"Authorization": f"Bearer {token}"},
        data={"text": "ACME SUPPLIES LLC"},
    )
    assert response.status_code == 401
