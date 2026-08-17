"""Voyage `voyage-3` embedding client — the only module touching Voyage AI.

Why Voyage and not local sentence-transformers (see the ADR in docs/):

* Anthropic ships **no embedding model** — embeddings must come from a
  separate provider or a self-hosted model.
* ``voyage-3`` returns 1024-dim vectors with strong retrieval quality on
  invoice/vendor text and needs no GPU. Local sentence-transformers (e.g.
  ``all-MiniLM-L6-v2``, 384-dim) are half the quality on domain text and
  would drag a heavy ``torch`` dependency + model download into the service
  image; for a corpus of thousands of bills (not millions), a hosted 1024-dim
  API at ~$0.02/1k docs is the right cost/quality point.

Contract with the Odoo side:

* Odoo POSTs batched text lists to ``POST /v1/embed`` (JWT-authenticated,
  same shared secret as ``/v1/extract``) and gets back a list of
  1024-dimensional vectors aligned with the input order.
* ``input_type="document"`` tells Voyage to optimize for retrieval-as-doc;
  the query side must use ``input_type="query"`` when the RAG step searches.

Hardening:

* **Batching** — ``voyage-3`` accepts up to 128 texts per request; larger
  batches are split and results concatenated in input order.
* **Retry** — 429/5xx/connection errors are retried once with a short
  backoff before surfacing a typed ``VoyageEmbeddingError``. A caller that
  sees the error keeps its rows ``ai_indexed=False`` and the cron retries
  the batch later — embedding must never crash the post pipeline.
* **Dimension assertion** — every response item must be a list of 1024
  floats. A silently-wrong dimension would poison the ``vector(1024)``
  column and the HNSW index; failing fast beats corrupting the index.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable

from .config import settings

_logger = logging.getLogger(__name__)

VOYAGE_MODEL = "voyage-3"
VOYAGE_DIMENSIONS = 1024
# voyage-3's documented per-request batch ceiling.
VOYAGE_MAX_BATCH = 128
# Two strikes per batch: one retry on transient upstream failure.
VOYAGE_RETRIES = 1
VOYAGE_RETRY_BACKOFF_SECONDS = 2.0


class VoyageEmbeddingError(Exception):
    """Raised when an embedding batch fails after retries or is malformed."""


class VoyageEmbedder:
    """Wraps the voyageai client with batching, retry and dimension checks.

    Injectable ``client`` seam so tests can run the full logic with a fake
    that returns canned vectors — no network, no API key.
    """

    def __init__(
        self,
        client=None,
        api_key: str | None = None,
        model: str = VOYAGE_MODEL,
    ):
        self._client = client
        self._api_key = api_key
        self._model = model

    def _ensure_client(self):
        """Lazily build the voyageai client on the first real embed.

        Tests inject a fake ``client`` so the SDK is never imported; a
        deployment without an embed call should not pay for the dependency
        or fail import. The SDK is imported here on purpose.
        """
        if self._client is None:
            import voyageai

            self._client = voyageai.Client(
                api_key=self._api_key or settings.voyage_api_key,
            )
        return self._client

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        """Embed many documents, returning one 1024-d vector per input.

        Batches at ``VOYAGE_MAX_BATCH`` and concats in input order. Every
        returned vector is asserted to be exactly 1024 floats.
        """
        batch = [text for text in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(batch), VOYAGE_MAX_BATCH):
            chunk = batch[start : start + VOYAGE_MAX_BATCH]
            vectors.extend(self._embed_one(chunk, input_type="document"))
        _logger.info(
            "voyage: embedded %d documents (model=%s dim=%d)",
            len(batch),
            self._model,
            VOYAGE_DIMENSIONS,
        )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed a single RAG query, optimized with ``input_type="query"``."""
        vectors = self._embed_one([text], input_type="query")
        return vectors[0]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _embed_one(self, texts: list[str], *, input_type: str) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(VOYAGE_RETRIES + 1):
            try:
                result = self._ensure_client().embed(
                    texts,
                    model=self._model,
                    input_type=input_type,
                )
                return self._normalize(result, expected=len(texts))
            except Exception as exc:  # voyageai raises its own hierarchy
                last_error = exc
                _logger.warning(
                    "voyage: embed attempt %d/%d failed for %d texts: %s",
                    attempt + 1,
                    VOYAGE_RETRIES + 1,
                    len(texts),
                    exc,
                )
                time.sleep(VOYAGE_RETRY_BACKOFF_SECONDS)
        assert last_error is not None
        raise VoyageEmbeddingError(
            f"voyage embedding failed after {VOYAGE_RETRIES + 1} attempts: "
            f"{last_error}",
        ) from last_error

    @staticmethod
    def _normalize(result, *, expected: int) -> list[list[float]]:
        """Extract and validate vectors from a voyageai Client.embed result.

        ``result.embeddings`` is a list of ``Embedding`` objects; each has a
        ``float_list`` attribute of exactly ``VOYAGE_DIMENSIONS`` floats.
        """
        raw = getattr(result, "embeddings", None)
        if raw is None:
            # Some SDK versions return dict-like objects or a bare list.
            raw = result if isinstance(result, list) else getattr(result, "data", [])
        extracted: list[list[float]] = []
        for item in raw:
            values = getattr(item, "float_list", None)
            if values is None and isinstance(item, dict):
                values = item.get("float_list") or item.get("embedding")
            if values is None and isinstance(item, (list, tuple)):
                values = item
            extracted.append([float(value) for value in values])

        if len(extracted) != expected:
            raise VoyageEmbeddingError(
                f"voyage returned {len(extracted)} vectors for {expected} texts",
            )
        for vector in extracted:
            if len(vector) != VOYAGE_DIMENSIONS:
                raise VoyageEmbeddingError(
                    f"voyage returned a {len(vector)}-dim vector; expected "
                    f"{VOYAGE_DIMENSIONS} (model={VOYAGE_MODEL})",
                )
        return extracted


def get_embedder() -> VoyageEmbedder:
    """FastAPI ``Depends()`` factory for the Voyage-backed embedder."""
    return VoyageEmbedder()
