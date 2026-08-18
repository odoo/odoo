"""FastAPI app: `POST /v1/extract` + `GET /healthz`.

Run with ``uvicorn app.main:app --reload``; interactive docs at ``/docs``.

The endpoint is an ``async def`` and the Claude call runs through
``AsyncAnthropic`` (an ``httpx.AsyncClient``), so a single uvicorn process
can concurrently await many extraction calls — unlike Odoo's prefork HTTP
workers, where one 5-20 s LLM round-trip pins an entire worker (measured in
docs/adr-003-ai-service.md: 33.5× login degradation with workers=2).
"""

import asyncio
import logging
import os
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from .auth import require_token
from .claude import ClaudeService
from .config import settings
from .dependencies import get_claude_service, get_embedder
from .embeddings import VoyageEmbedder, VoyageEmbeddingError
from .errors import (
    BadRequestError,
    ServiceError,
    UnsupportedMediaTypeError,
    UploadTooLargeError,
)
from .ocr import extract_bytes
from .schemas import (
    EmbedRequest,
    EmbedResponse,
    ExtractionResponse,
    HealthResponse,
)

_logger = logging.getLogger(__name__)

# Build provenance for /healthz. INVOICE_AI_BUILD_SHA is stamped by the
# Dockerfile builder stage (git rev-parse --short HEAD); defaults to
# "dev" when running from a checkout so local uvicorn never fails.
BUILD_SHA = os.environ.get("INVOICE_AI_BUILD_SHA", "dev")

app = FastAPI(
    title="invoice-ai",
    version="1.0.0",
    description="Standalone vendor invoice extraction service (ADR-003). "
    "Owns OCR + the Claude call so Odoo HTTP workers are never blocked.",
)


# ---------------------------------------------------------------------------
# Error envelope — mirrors docs/openapi.yaml ErrorEnvelope.
# ---------------------------------------------------------------------------
def _error_payload(exc: ServiceError) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": exc.code,
        "message": exc.message,
    }
    if exc.retry_after_seconds is not None:
        error["retry_after_seconds"] = exc.retry_after_seconds
    if exc.details:
        error["details"] = exc.details
    return {"error": error}


@app.exception_handler(ServiceError)
async def _service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    _logger.warning("invoice-ai error %s: %s", exc.code, exc.message)
    return JSONResponse(status_code=exc.status_code, content=_error_payload(exc))


@app.exception_handler(Exception)
async def _unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    _logger.exception("unexpected invoice-ai error: %r", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "E5000",
                "message": "Internal service error",
            }
        },
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> dict[str, str]:
    """Liveness probe (OpenAPI /healthz).

    Open to unauthenticated callers — the compose healthcheck curls this
    without a JWT. Carries the build SHA so a deployed image can be traced
    back to the git revision that produced it.
    """
    return {"status": "ok", "build_sha": BUILD_SHA}


@app.post("/v1/extract", response_model=ExtractionResponse)
async def extract_invoice(
    claude: Annotated[ClaudeService, Depends(get_claude_service)],
    _auth: Annotated[dict, Depends(require_token)],
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
    effort: Annotated[str, Form()] = "normal",
) -> dict[str, Any]:
    """Extract structured invoice data from a PDF/image or OCR text.

    Either ``file`` (multipart upload, PDF or PNG/JPEG/TIFF, max 10 MiB) or
    ``text`` (pre-OCR'd text) must be provided. A document goes through
    Tesseract (app/ocr.py) first; the resulting text is sent to Claude with
    the frozen prompts/v3.md system prefix (cached) and
    ``output_format=InvoiceExtraction``.
    """
    if file is None and not text:
        raise BadRequestError("Provide either 'file' (PDF/image) or 'text'.")

    if file is not None:
        raw = await file.read()
        if len(raw) > settings.max_upload_bytes:
            raise UploadTooLargeError(
                f"Upload of {len(raw)} bytes exceeds the "
                f"{settings.max_upload_bytes} byte limit.",
            )
        mimetype = (file.content_type or "").lower()
        if not mimetype or (
            mimetype != "application/pdf"
            and not mimetype.startswith("image/")
        ):
            raise UnsupportedMediaTypeError(
                f"Unsupported mimetype '{mimetype or 'unknown'}'. Only PDF and "
                "image/* uploads are accepted.",
            )
        ocr_result = await asyncio.to_thread(
            extract_bytes, raw, mimetype, file.filename or "",
        )
        text = ocr_result["text"]

    result = await claude.extract(text=text or "", effort=effort)
    return {
        "extraction": result["parsed"].model_dump(mode="json"),
        "usage": result["usage"],
        "model": result["model"],
    }


@app.exception_handler(VoyageEmbeddingError)
async def _voyage_error_handler(_: Request, exc: VoyageEmbeddingError) -> JSONResponse:
    """Voyage upstream failure -> 503 (same envelope as Claude upstream).

    The Odoo embed cron keeps its rows ``ai_indexed=False`` and retries
    later; embedding must never look like a 500 internal error.
    """
    _logger.warning("invoice-ai embed error 503: %s", exc)
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "E5032",
                "message": "Embedding service unavailable",
            }
        },
    )


@app.post("/v1/embed", response_model=EmbedResponse)
async def embed_texts(
    embedder: Annotated[VoyageEmbedder, Depends(get_embedder)],
    _auth: Annotated[dict, Depends(require_token)],
    payload: EmbedRequest,
) -> dict[str, Any]:
    """Embed raw documents with Voyage `voyage-3`.

    Body: ``{"texts": ["...", ...]}``. Returns one 1024-dim vector per input,
    in order. Odoo calls this from the vendor-doc backfill cron and the
    post-pipeline embed job; the model/dimensions are echoed so the Odoo
    side can assert its ``vector(1024)`` column matches.
    """
    texts = payload.texts
    if not texts or any(not (text or "").strip() for text in texts):
        raise BadRequestError("Provide at least one non-empty text to embed.")
    vectors = embedder.embed_documents(texts)
    return {
        "vectors": vectors,
        "model": settings.voyage_model,
        "dimensions": settings.voyage_dimensions,
    }
