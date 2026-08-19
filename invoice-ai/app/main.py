"""FastAPI app: `POST /v1/extract` + `GET /healthz` + `POST /rag/vendor-context`.

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
import time
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .auth import require_token
from .claude import ClaudeService
from .config import settings
from .metrics import (
    CLAUDE_API_DURATION,
    CLAUDE_TOKENS_TOTAL,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
    OCR_DURATION,
    Timer,
    record_claude_tokens,
)
from .dependencies import get_claude_service, get_embedder
from .embeddings import VoyageEmbedder, VoyageEmbeddingError
from .errors import (
    BadRequestError,
    RAGUnavailableError,
    ServiceError,
    UnsupportedMediaTypeError,
    UploadTooLargeError,
)
from .ocr import extract_bytes
from .retrieve import close_pool, retrieve_vendor_context
from .schemas import (
    EmbedRequest,
    EmbedResponse,
    ExtractionResponse,
    HealthResponse,
    VendorContextRequest,
    VendorContextResponse,
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

# --- Rate limiting (OWASP A04 — Insecure Design) ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Prometheus /metrics endpoint — scraped by Prometheus every 15s
# ---------------------------------------------------------------------------
from prometheus_client import make_asgi_app  # noqa: E402

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ---------------------------------------------------------------------------
# Lifecycle — shut down the asyncpg pool on shutdown
# ---------------------------------------------------------------------------
@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_pool()


# ---------------------------------------------------------------------------
# Prometheus HTTP middleware — records every request as a Counter + Histogram
# ---------------------------------------------------------------------------
@app.middleware("http")
async def _prometheus_middleware(request: Request, call_next: Any) -> Any:
    """Track HTTP request rate, errors, and duration for the RED method.

    Skips the /metrics endpoint itself to avoid self-referential inflation.
    """
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    path = request.url.path
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start

    status = str(response.status_code)
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status=status).inc()
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=path, status=status).observe(
        elapsed,
    )
    return response


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
@limiter.limit("10/minute")
async def extract_invoice(
    request: Request,
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
        # Track OCR duration — histogram for the RED method
        with Timer(OCR_DURATION):
            ocr_result = await asyncio.to_thread(
                extract_bytes, raw, mimetype, file.filename or "",
            )
        text = ocr_result["text"]

    # Track Claude API latency — histogram labeled by model
    model_name = settings.anthropic_model
    with Timer(CLAUDE_API_DURATION, model=model_name):
        result = await claude.extract(text=text or "", effort=effort)

    # Record token consumption — counter for daily cost tracking
    record_claude_tokens(model=result["model"], usage=result["usage"])

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
@limiter.limit("30/minute")
async def embed_texts(
    request: Request,
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


# ---------------------------------------------------------------------------
# RAG vendor-context endpoint (Phase 1 — Step 3)
# ---------------------------------------------------------------------------


@app.post("/rag/vendor-context", response_model=VendorContextResponse)
@limiter.limit("20/minute")
async def vendor_context(
    request: Request,
    embedder: Annotated[VoyageEmbedder, Depends(get_embedder)],
    _auth: Annotated[dict, Depends(require_token)],
    payload: VendorContextRequest,
) -> dict[str, Any]:
    """Retrieve vendor context for RAG validation.

    JWT-protected.  Embeds the OCR text with ``input_type="query"``
    (asymmetric: documents were embedded with ``input_type="document"``),
    runs hybrid vector + ref + VAT/name retrieval over
    ``invoice_agent_vendor_doc``, deduplicates by ``move_id``, and returns
    the top-8 candidates alongside the vendor's GL account frequency
    distribution.

    The Odoo consumer calls this after extraction to feed the validation
    step (Phase 2) with historical context.
    """
    partner_id = payload.partner_id
    if partner_id <= 0:
        raise BadRequestError("partner_id must be a positive integer.")

    ocr_text = (payload.ocr_text or "").strip()
    if not ocr_text:
        raise BadRequestError("ocr_text must not be empty.")

    try:
        context = await retrieve_vendor_context(
            partner_id=partner_id,
            ocr_text=ocr_text,
            embedder=embedder,
            extracted_ref=payload.extracted_ref,
            extracted_vat=payload.extracted_vat,
            extracted_vendor_name=payload.extracted_vendor_name,
        )
    except RuntimeError as exc:
        _logger.warning("retrieve_vendor_context failed: %s", exc)
        raise RAGUnavailableError(
            message=f"RAG retrieval unavailable: {exc}",
        ) from exc
    except Exception as exc:
        _logger.exception("retrieve_vendor_context error: %r", exc)
        raise ServiceError(
            message="Internal retrieval error",
            code="E5000",
        ) from exc

    return {
        "candidates": context["candidates"],
        "gl_account_frequencies": context["gl_account_frequencies"],
        "query_embedding_model": context["query_embedding_model"],
    }
