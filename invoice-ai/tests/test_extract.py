"""Endpoint tests for POST /v1/extract and GET /healthz.

Runs through httpx.ASGITransport (no network, no Anthropic SDK call) with the
Claude service mocked at the FastAPI dependency seam — the same "mock the
client, test the contract" approach the Odoo suite uses.

JWT auth (week's brief): `/v1/extract` requires a valid Bearer JWT
(``Depends(require_token)``); ``/healthz`` stays open for the compose
healthcheck. Positive-path tests carry the ``auth_headers`` fixture; the
negative JWT matrix lives in ``test_auth.py``.

Coverage required by the week's brief:
  * happy path — text input returns InvoiceExtraction + usage
  * PDF upload path — OCR runs first, then Claude on the OCR text
  * oversized upload -> 413
  * bad mimetype -> 415
  * upstream RateLimitError -> 503 (clean envelope, retry_after_seconds)
"""

import pytest

from app.errors import ClaudeRateLimitError


@pytest.mark.anyio
async def test_healthz(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # Build provenance is stamped on the probe so a deployed image can be
    # traced to the git revision it was built from.
    assert body["build_sha"]


@pytest.mark.anyio
async def test_extract_happy_path_text(fake_claude, client, default_result, auth_headers):
    fake_claude.result = default_result

    response = await client.post(
        "/v1/extract",
        headers=auth_headers,
        data={"text": "ACME SUPPLIES LLC\nTOTAL USD 1,350.00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["extraction"]["vendor_name"] == "ACME SUPPLIES LLC"
    assert body["extraction"]["amount_total"] == "1350.00"
    assert body["extraction"]["currency"] == "USD"
    assert body["extraction"]["lines"][0]["name"] == "Server hosting"
    assert body["usage"]["cache_read_input_tokens"] == 4400
    assert body["model"] == "claude-opus-4-8"
    # The service must pass the raw OCR text straight to the model.
    assert fake_claude.last_args["text"] == (
        "ACME SUPPLIES LLC\nTOTAL USD 1,350.00"
    )


@pytest.mark.anyio
async def test_extract_with_pdf_upload_runs_ocr(
    fake_claude, client, default_result, monkeypatch, auth_headers,
):
    """A PDF upload goes through OCR first, then Claude on the OCR text."""
    fake_claude.result = default_result

    def fake_ocr(raw, mimetype, filename):
        assert mimetype == "application/pdf"
        return {"text": "OCR-DERIVED TEXT\nTOTAL EUR 100.00", "confidence": 0.9}

    monkeypatch.setattr("app.main.extract_bytes", fake_ocr)

    response = await client.post(
        "/v1/extract",
        headers=auth_headers,
        files={"file": ("invoice.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 200
    assert fake_claude.last_args["text"] == (
        "OCR-DERIVED TEXT\nTOTAL EUR 100.00"
    )


@pytest.mark.anyio
async def test_extract_missing_both_file_and_text_returns_400(client, auth_headers):
    response = await client.post("/v1/extract", headers=auth_headers, data={})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "E4001"


@pytest.mark.anyio
async def test_extract_oversized_upload_returns_413(fake_claude, client, auth_headers):
    # 11 MiB of zeros — over the 10 MiB service limit.
    oversized = b"\0" * (11 * 1024 * 1024)
    response = await client.post(
        "/v1/extract",
        headers=auth_headers,
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "E4131"


@pytest.mark.anyio
async def test_extract_bad_mimetype_returns_415(fake_claude, client, auth_headers):
    response = await client.post(
        "/v1/extract",
        headers=auth_headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "E4151"


@pytest.mark.anyio
async def test_extract_upstream_rate_limit_maps_to_503(fake_claude, client, auth_headers):
    fake_claude.error = ClaudeRateLimitError(
        message="Anthropic rate limit (HTTP 429)",
        retry_after_seconds=17,
    )
    response = await client.post(
        "/v1/extract",
        headers=auth_headers,
        data={"text": "ACME SUPPLIES LLC\nTOTAL USD 1,350.00"},
    )
    # The client contract: any upstream AI failure is 503 Service
    # Unavailable, with the back-off hint preserved in the envelope.
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "E5031"
    assert body["error"]["retry_after_seconds"] == 17


@pytest.mark.anyio
async def test_extract_upstream_generic_error_maps_to_503(fake_claude, client, auth_headers):
    fake_claude.error = ClaudeRateLimitError(
        message="Anthropic API error",
    )
    response = await client.post(
        "/v1/extract",
        headers=auth_headers,
        data={"text": "ACME SUPPLIES LLC"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "E5031"
