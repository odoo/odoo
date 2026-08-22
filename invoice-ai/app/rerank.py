"""Voyage `rerank-2.5` reranking client — the second stage of two-stage retrieval.

After the initial cosine-similarity recall (top-30 candidates from pgvector),
this module re-scores those candidates against the query using Voyage's
cross-encoder reranker. Cross-encoders see the query and document *together*
(sent to the model as a single input pair), which is far more precise than
the asymmetric embedding distance used in the recall stage.

Pipeline position::

    retrieve.hybrid_retrieve(top-30)  →  rerank.rerank(top-30 → top-5)
        →  validate.validate_extraction(top-5)

Why a separate module from embeddings.py:

* Different SDK method (``client.rerank`` vs ``client.embed``).
* Different data flow: input is (query, list[str]) → list[ScoredResult].
* Injectable seam: tests inject a fake reranker that returns canned
  relevance scores; the SDK is never imported in test mode.

Hardening:

* **Retry** — 429/5xx/connection errors are retried once with a short
  backoff before surfacing a ``VoyageRerankError``. The caller degrades
  to the original cosine ordering (recall-only) instead of failing the
  whole pipeline.
* **Dimension/type assertion** — every result must carry an ``index``
  (int) and ``relevance_score`` (float). Malformed upstream responses
  fail fast rather than silently shuffling the candidate list.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from .config import settings

_logger = logging.getLogger(__name__)

RERANK_MODEL = "rerank-2.5"
RERANK_TOP_K = 5
RERANK_RETRIES = 1
RERANK_RETRY_BACKOFF_SECONDS = 2.0


class VoyageRerankError(Exception):
    """Raised when a rerank call fails after retries or returns malformed data."""


class VoyageReranker:
    """Cross-encoder reranker wrapping ``voyageai.Client().rerank()``.

    Injectable ``client`` seam so tests can run the full validation
    pipeline with canned scores — no network, no API key.
    """

    def __init__(
        self,
        client: Any | None = None,
        api_key: str | None = None,
        model: str = RERANK_MODEL,
    ) -> None:
        self._client: Any | None = client
        self._api_key = api_key
        self._model = model

    def _ensure_client(self) -> Any:
        """Lazily build the voyageai client on the first real rerank."""
        if self._client is None:
            import voyageai

            self._client = voyageai.Client(
                api_key=self._api_key or settings.voyage_api_key,
            )
        return self._client

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = RERANK_TOP_K,
    ) -> list[dict[str, Any]]:
        """Rerank *documents* against *query* and return the top_k results.

        Each result is ``{"index": int, "relevance_score": float,
        "original_text": str}``.  Results are sorted by descending
        relevance_score (most relevant first).

        On transient failure, raises ``VoyageRerankError`` — the caller
        falls back to the original cosine ordering.
        """
        if not documents:
            return []

        last_error: Exception | None = None
        for attempt in range(RERANK_RETRIES + 1):
            try:
                result = self._ensure_client().rerank(
                    query=query,
                    documents=documents,
                    model=self._model,
                    top_k=min(top_k, len(documents)),
                )
                return self._normalize(result, documents)
            except Exception as exc:
                last_error = exc
                _logger.warning(
                    "voyage rerank attempt %d/%d failed for %d docs: %s",
                    attempt + 1,
                    RERANK_RETRIES + 1,
                    len(documents),
                    exc,
                )
                if attempt < RERANK_RETRIES:
                    time.sleep(RERANK_RETRY_BACKOFF_SECONDS)

        assert last_error is not None
        raise VoyageRerankError(
            f"voyage rerank failed after {RERANK_RETRIES + 1} attempts: {last_error}",
        ) from last_error

    @staticmethod
    def _normalize(result: Any, documents: list[str]) -> list[dict[str, Any]]:
        """Extract and validate rerank results into a uniform dict list."""
        raw_results = getattr(result, "results", None)
        if raw_results is None:
            raw_results = result if isinstance(result, list) else []

        normalized: list[dict[str, Any]] = []
        for item in raw_results:
            index = getattr(item, "index", None)
            score = getattr(item, "relevance_score", None)
            if index is None or score is None:
                # Some SDK versions use dict-like results
                if isinstance(item, dict):
                    index = item.get("index")
                    score = item.get("relevance_score")
            if index is None or score is None:
                raise VoyageRerankError(f"malformed rerank result (no index/score): {item!r}")
            index = int(index)
            score = float(score)
            if 0 <= index < len(documents):
                normalized.append(
                    {
                        "index": index,
                        "relevance_score": score,
                        "original_text": documents[index],
                    }
                )
            else:
                _logger.warning(
                    "voyage rerank: result index %d out of range for %d docs",
                    index,
                    len(documents),
                )

        # Sort by descending relevance_score
        normalized.sort(key=lambda r: r["relevance_score"], reverse=True)
        _logger.info(
            "voyage rerank: %d results (model=%s)",
            len(normalized),
            RERANK_MODEL,
        )
        return normalized


def get_reranker() -> VoyageReranker:
    """FastAPI ``Depends()`` factory for the Voyage-backed reranker."""
    return VoyageReranker()
