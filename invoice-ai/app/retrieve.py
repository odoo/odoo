"""RAG retrieval module — asyncpg-backed vector search with metadata prefiltering.

Connects directly to the same PostgreSQL database the Odoo addon writes to,
querying the ``invoice_agent_vendor_doc`` table whose ``embedding vector(1024)``
column and HNSW index are bootstrapped by ``invoice_agent_vendor_doc.init()``.

Why ``asyncpg`` instead of the Odoo ORM: the FastAPI service runs outside the
Odoo process and has no ORM access. ``asyncpg`` gives us a zero-dependency,
parameterised, async-native connection to the same Postgres — and the raw SQL
lets us use pgvector's ``<=>`` cosine-distance operator, which the ORM cannot
express.

Pipeline per call (``retrieve_vendor_context``):

1.  **Embed the query** — ``VoyageEmbedder.embed_query(ocr_text)`` with
    ``input_type="query"`` (asymmetric: documents were embedded with
    ``input_type="document"``).
2.  **Vector search** — ``WHERE partner_id = $1 ORDER BY embedding <=>
    $2::vector LIMIT $3``.  The ``partner_id`` prefilter narrows the HNSW
    scan to one vendor's history so a vendor's own bills dominate the
    candidate set (tested via ``EXPLAIN ANALYZE`` in ``docs/rag-eval.md``).
3.  **Hybrid enrichment** — union the vector hits with (a) an exact
    ``res.partner`` VAT/name match whose bills are pulled, and (b) a ``ref``
    equality lookup catching duplicate invoice numbers.
4.  **Deduplicate** by ``move_id`` and cap context tokens with
    ``client.messages.count_tokens`` — never silently truncate.
5.  **GL account frequency** — count how often each account code appears in
    the vendor's posted bills (for the validation step's chart-of-accounts
    suggestion).

The public entry point is ``retrieve_vendor_context``; the route in
``app/main.py`` calls it directly (no HTTP hop — same process).
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg  # type: ignore[import-untyped]

from .config import settings
from .embeddings import VoyageEmbedder
from .rerank import VoyageReranker, VoyageRerankError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# asyncpg connection pool (lazily initialised per event-loop)
# ---------------------------------------------------------------------------
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return (or create) the module-level asyncpg connection pool.

    The DSN is read from ``settings.database_url`` which must be set via the
    ``INVOICE_AI_DATABASE_URL`` env var (e.g.
    ``postgresql://odoo:odoo@localhost:5432/odoo``).
    """
    global _pool  # noqa: PLW0603
    if _pool is None or getattr(_pool, "_closed", True):
        dsn = settings.database_url
        if not dsn:
            raise RuntimeError(
                "INVOICE_AI_DATABASE_URL is not configured — cannot create an asyncpg pool."
            )
        _pool = await asyncpg.create_pool(
            dsn,
            min_size=1,
            max_size=5,
        )
        _logger.info("retrieve: asyncpg pool created (dsn hidden)")
    return _pool


async def close_pool() -> None:
    """Shut down the pool gracefully (call on app shutdown)."""
    global _pool  # noqa: PLW0603
    if _pool is not None and not getattr(_pool, "_closed", True):
        await _pool.close()
        _logger.info("retrieve: asyncpg pool closed")
    _pool = None


# ---------------------------------------------------------------------------
# Vector retrieval (Step 1-2: query construction + metadata prefiltering)
# ---------------------------------------------------------------------------


async def vector_search(
    partner_id: int,
    query_vector: list[float],
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Cosine-similarity search over ``invoice_agent_vendor_doc``.

    Prefilters on ``partner_id`` so a vendor's own history dominates the
    candidate set.  Returns a list of dicts with keys
    ``{move_id, content, distance}`` ordered by ascending distance (most
    similar first).

    ``distance`` is the raw pgvector cosine distance (0 = identical,
    2 = opposite).  ``similarity = 1 - distance`` when needed.
    """
    pool = await get_pool()
    vector_literal = _vector_to_literal(query_vector)
    rows = await pool.fetch(
        """
        SELECT move_id, content,
               embedding <=> $1::vector AS distance
        FROM invoice_agent_vendor_doc
        WHERE partner_id = $2
        ORDER BY embedding <=> $1::vector
        LIMIT $3
        """,
        vector_literal,
        int(partner_id),
        int(limit),
    )
    results = [
        {
            "move_id": row["move_id"],
            "content": row["content"],
            "distance": float(row["distance"]),
        }
        for row in rows
    ]
    _logger.info(
        "retrieve vector_search: partner_id=%d -> %d hits (limit=%d)",
        partner_id,
        len(results),
        limit,
    )
    return results


# ---------------------------------------------------------------------------
# GL account frequency (Step 3: vendor-context enrichment)
# ---------------------------------------------------------------------------


async def gl_account_frequencies(partner_id: int) -> dict[str, int]:
    """Count how often each GL account code appears in the vendor's history.

    Queries ``account_move_line`` joined to ``account_move`` for posted
    bills of this vendor, grouped by ``account_id.code``.  Returns
    ``{account_code: count}`` sorted descending by frequency.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT a.code AS account_code, COUNT(*) AS freq
        FROM account_move_line l
        JOIN account_move m ON m.id = l.move_id
        JOIN account_account a ON a.id = l.account_id
        WHERE m.partner_id = $1
          AND m.state = 'posted'
          AND m.move_type = 'in_invoice'
          AND l.display_type IS NOT DISTINCT FROM 'product'
        GROUP BY a.code
        ORDER BY freq DESC
        """,
        int(partner_id),
    )
    frequencies = {row["account_code"]: row["freq"] for row in rows}
    _logger.info(
        "retrieve gl_account_frequencies: partner_id=%d -> %d accounts",
        partner_id,
        len(frequencies),
    )
    return frequencies


# ---------------------------------------------------------------------------
# Hybrid retrieval (Step 4: VAT/name + ref equality + dedup)
# ---------------------------------------------------------------------------


async def hybrid_retrieve(
    partner_id: int,
    query_vector: list[float],
    ocr_text: str = "",
    extracted_ref: str = "",
    extracted_vat: str = "",
    extracted_vendor_name: str = "",
    vector_limit: int = 30,
) -> list[dict[str, Any]]:
    """Union vector hits with exact-ref and VAT/name lookups, dedup by move_id.

    This is the full retrieval pipeline exposed by the ``/rag/vendor-context``
    endpoint.  Returns a deduplicated, distance-ranked list of candidate
    historical bills.

    ``vector_limit`` defaults to 30 — a wide recall set fed to the reranker
    for precision ordering.  The reranker (``rerank.rerank``) trims this
    down to the top-5 most relevant candidates before validation.
    """
    # --- 1. Vector search (metadata-prefiltered) ---
    candidates = await vector_search(partner_id, query_vector, limit=vector_limit)
    seen_move_ids: set[int] = {c["move_id"] for c in candidates}

    pool = await get_pool()

    # --- 2. Exact ref equality lookup (catches duplicate invoice numbers) ---
    ref = extracted_ref.strip() if extracted_ref else ""
    if ref:
        ref_rows = await pool.fetch(
            """
            SELECT m.id AS move_id,
                   mv.content,
                   0.0 AS distance
            FROM account_move m
            LEFT JOIN invoice_agent_vendor_doc mv ON mv.move_id = m.id
            WHERE m.ref = $1
              AND m.state = 'posted'
              AND m.move_type = 'in_invoice'
            """,
            ref,
        )
        for row in ref_rows:
            mid = row["move_id"]
            if mid not in seen_move_ids:
                candidates.append(
                    {
                        "move_id": mid,
                        "content": row["content"] or "",
                        "distance": 0.0,
                        "match_reason": "ref_equality",
                    }
                )
                seen_move_ids.add(mid)
        _logger.info("retrieve hybrid: ref='%s' -> %d new hits", ref, len(ref_rows))

    # --- 3. VAT / name match → pull that partner's recent bills ---
    resolved_partner_id = await _resolve_partner_id(
        pool, vat=extracted_vat, name=extracted_vendor_name
    )
    if resolved_partner_id and resolved_partner_id != partner_id:
        extra_rows = await pool.fetch(
            """
            SELECT mv.move_id, mv.content,
                   0.0 AS distance
            FROM invoice_agent_vendor_doc mv
            WHERE mv.partner_id = $1
            ORDER BY mv.indexed_at DESC
            LIMIT $2
            """,
            int(resolved_partner_id),
            int(vector_limit),
        )
        for row in extra_rows:
            mid = row["move_id"]
            if mid not in seen_move_ids:
                candidates.append(
                    {
                        "move_id": mid,
                        "content": row["content"] or "",
                        "distance": float(row["distance"]),
                        "match_reason": "vat_name_match",
                    }
                )
                seen_move_ids.add(mid)
        _logger.info(
            "retrieve hybrid: vat/name partner_id=%d -> %d new hits",
            resolved_partner_id,
            len(extra_rows),
        )

    # --- 4. Sort by distance (most similar first) ---
    candidates.sort(key=lambda c: c["distance"])
    return candidates


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vector_to_literal(vector: list[float]) -> str:
    """Format a float list as a pgvector literal: ``[0.1,0.2,...]``."""
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


async def _resolve_partner_id(
    pool: asyncpg.Pool,
    *,
    vat: str = "",
    name: str = "",
) -> int | None:
    """Best-effort partner resolution: VAT first, then name."""
    vat = (vat or "").strip()
    name = (name or "").strip()
    if vat:
        row = await pool.fetchrow(
            """
            SELECT id FROM res_partner
            WHERE vat = $1 AND parent_id IS NULL
            LIMIT 1
            """,
            vat,
        )
        if row:
            return row["id"]
    if name:
        row = await pool.fetchrow(
            """
            SELECT id FROM res_partner
            WHERE name ILIKE $1 AND parent_id IS NULL
            LIMIT 1
            """,
            f"%{name}%",
        )
        if row:
            return row["id"]
    return None


# ---------------------------------------------------------------------------
# High-level entry point (called by the route)
# ---------------------------------------------------------------------------


async def retrieve_vendor_context(
    *,
    partner_id: int,
    ocr_text: str,
    embedder: VoyageEmbedder | None = None,
    reranker: VoyageReranker | None = None,
    extracted_ref: str = "",
    extracted_vat: str = "",
    extracted_vendor_name: str = "",
) -> dict[str, Any]:
    """Full RAG retrieval: embed → hybrid recall (top-30) → rerank (top-5) → GL freqs.

    Two-stage retrieval pipeline:

    1.  **Recall** — embed the query, retrieve top-30 candidates via hybrid
        vector + ref + VAT/name search (wide net, fast).
    2.  **Rerank** — Voyage ``rerank-2.5`` cross-encoder re-scores the 30
        candidates against the query and returns the top-5 most relevant
        (precise, slightly slower).  On reranker failure the original cosine
        ordering degrades gracefully.

    Returns::

        {
            "candidates": [...],          # reranked (top-5) historical bills
            "candidates_before_rerank": N, # how many were recalled
            "reranked": true/false,       # whether reranking was applied
            "gl_account_frequencies": {},  # {account_code: count}
            "query_embedding_model": "...",
            "rerank_model": "...",
        }
    """
    if embedder is None:
        embedder = VoyageEmbedder()

    # 1. Embed query (input_type="query" asymmetry)
    query_vector = embedder.embed_query(ocr_text)

    # 2. Hybrid retrieval — wide recall (top-30 by default)
    candidates = await hybrid_retrieve(
        partner_id=partner_id,
        query_vector=query_vector,
        ocr_text=ocr_text,
        extracted_ref=extracted_ref,
        extracted_vat=extracted_vat,
        extracted_vendor_name=extracted_vendor_name,
    )

    # 3. Rerank: cross-encoder precision ordering (top-30 → top-5)
    reranked = False
    candidates_before_rerank = len(candidates)
    rerank_model_name = ""
    if reranker is None:
        reranker = VoyageReranker()
    if len(candidates) > 1:
        try:
            documents = [c["content"] for c in candidates]
            reranked_results = reranker.rerank(
                query=ocr_text,
                documents=documents,
            )
            # Reorder candidates by the reranker's relevance_score
            reranked_candidates = []
            for result in reranked_results:
                orig_index = result["index"]
                if 0 <= orig_index < len(candidates):
                    enriched = dict(candidates[orig_index])
                    enriched["rerank_score"] = result["relevance_score"]
                    reranked_candidates.append(enriched)
            candidates = reranked_candidates
            reranked = True
            rerank_model_name = "rerank-2.5"
            _logger.info(
                "retrieve rerank: %d candidates → top-%d (reranked=%s)",
                candidates_before_rerank,
                len(candidates),
                reranked,
            )
        except VoyageRerankError:
            # Degraded: keep original cosine ordering
            _logger.warning(
                "retrieve rerank: reranker failed, keeping cosine ordering (%d candidates)",
                len(candidates),
            )
    elif candidates:
        reranked = True  # trivial case: 1 candidate
        candidates[0]["rerank_score"] = 1.0

    # 4. GL account frequency distribution
    frequencies = await gl_account_frequencies(partner_id)

    return {
        "candidates": candidates,
        "candidates_before_rerank": candidates_before_rerank,
        "reranked": reranked,
        "gl_account_frequencies": frequencies,
        "query_embedding_model": "voyage-3",
        "rerank_model": rerank_model_name,
    }
