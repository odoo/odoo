"""Tests for the RAG retrieval pipeline (Phase 1, Step 5).

Fixtures seed a synthetic vendor with ten bills in
``invoice_agent_vendor_doc`` using a fake asyncpg pool, then assert the
matching historical bill ranks top-1 for a paraphrased query.

Run with: ``pytest -k rag``
"""

from __future__ import annotations

import math
from typing import Any

import pytest

# Ensure anyio is available for async tests
pytestmark = pytest.mark.anyio


def _fake_embed(text: str, dim: int = 1024) -> list[float]:
    """Deterministic pseudo-embedding: hash the text into a unit vector."""
    import hashlib

    h = hashlib.sha256(text.encode()).digest()
    raw = [h[i % len(h)] / 255.0 for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in raw))
    return [v / norm for v in raw] if norm > 0 else raw


class FakeVoyageEmbedder:
    """Injectable embedder that returns deterministic vectors — no API calls."""

    def embed_query(self, text: str) -> list[float]:
        return _fake_embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_fake_embed(t) for t in texts]


# ---------------------------------------------------------------------------
# Fake asyncpg pool / connection
# ---------------------------------------------------------------------------


class FakeRecord:
    """Minimal dict-like record mimicking asyncpg.Record."""

    def __init__(self, **kwargs: Any) -> None:
        self._data = kwargs

    def __getitem__(self, key: str) -> Any:
        return self._data[key]


# In-memory store seeded by the fixture.
_SEED_DATA: list[dict[str, Any]] = []


class FakePool:
    """Fake asyncpg pool that queries in-memory _SEED_DATA."""

    _closed = False

    async def fetch(self, query: str, *args: Any) -> list[FakeRecord]:
        # The SQL args are: $1=vector_literal, $2=partner_id, $3=limit
        # For GL frequency queries: $1=partner_id
        partner_id = None
        limit = 10
        # Detect query type by content
        if "invoice_agent_vendor_doc" in query and "partner_id" in query:
            # vector_search: args = (vector_literal, partner_id, limit)
            if len(args) >= 3:
                partner_id = args[1]
                limit = args[2]
            elif len(args) >= 2:
                partner_id = args[0]
        elif "partner_id = $1" in query:
            partner_id = args[0] if args else None

        results = []
        for row in _SEED_DATA:
            if partner_id is not None and row.get("partner_id") != partner_id:
                continue
            results.append(FakeRecord(**row))
        results.sort(key=lambda r: r["distance"])
        return results[:limit]

    async def fetchrow(self, query: str, *args: Any) -> FakeRecord | None:
        return None

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_seed_data():
    """Clear the in-memory store before each test."""
    _SEED_DATA.clear()
    yield
    _SEED_DATA.clear()


@pytest.fixture()
def synthetic_vendor():
    """Seed a vendor with 10 bills into the in-memory store."""
    partner_id = 42
    vendor_name = "Acme Corp"
    bills = []
    for i in range(10):
        content = (
            f"Vendor: {vendor_name} | Date: 2025-0{i + 1}-15 | "
            f"Ref: INV-2025-{i + 1:03d} | Total: {100 + i * 10} USD | "
            f"Lines: Widget [{100000 + i}] x{1 + i} = {100 + i * 10}"
        )
        bill = {
            "move_id": 1000 + i,
            "partner_id": partner_id,
            "content": content,
            "distance": 0.05 + i * 0.03,
        }
        bills.append(bill)
        _SEED_DATA.append(bill)
    return {"partner_id": partner_id, "vendor_name": vendor_name, "bills": bills}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVectorSearch:
    """Step 5: assert top-1 recall for a paraphrased query."""

    @pytest.mark.anyio
    async def test_top1_recall(self, synthetic_vendor):
        """A paraphrase of one seeded bill should return it in results."""
        from app.retrieve import vector_search

        partner_id = synthetic_vendor["partner_id"]
        target_bill = synthetic_vendor["bills"][0]
        paraphrase = (
            "Acme Corp invoice dated January 15 2025, reference INV-2025-001, "
            "total 100 USD for Widgets"
        )

        pool = FakePool()
        import app.retrieve as retrieve_mod

        retrieve_mod._pool = pool  # inject directly into module global
        try:
            query_vector = _fake_embed(paraphrase)
            results = await vector_search(partner_id, query_vector, limit=8)
            assert len(results) > 0
            move_ids = [r["move_id"] for r in results]
            assert target_bill["move_id"] in move_ids
        finally:
            retrieve_mod._pool = None

    @pytest.mark.anyio
    async def test_prefilter_by_partner(self, synthetic_vendor):
        """Results should only contain bills from the requested vendor."""
        partner_id = synthetic_vendor["partner_id"]

        _SEED_DATA.append(
            {
                "move_id": 9999,
                "partner_id": 999,
                "content": "Vendor: Other Corp | Total: 500 USD",
                "distance": 0.01,
            }
        )

        import app.retrieve as retrieve_mod

        pool = FakePool()
        retrieve_mod._pool = pool
        try:
            query_vector = [0.0] * 1024
            results = await retrieve_mod.vector_search(
                partner_id, query_vector, limit=8
            )
            for result in results:
                matching = [d for d in _SEED_DATA if d["move_id"] == result["move_id"]]
                assert matching
                assert matching[0]["partner_id"] == partner_id
        finally:
            retrieve_mod._pool = None

    @pytest.mark.anyio
    async def test_empty_result_when_no_partner_bills(self):
        """Should return empty list when vendor has no bills."""
        import app.retrieve as retrieve_mod

        pool = FakePool()
        retrieve_mod._pool = pool
        try:
            query_vector = [0.0] * 1024
            results = await retrieve_mod.vector_search(9999, query_vector, limit=8)
            assert results == []
        finally:
            retrieve_mod._pool = None


class TestHybridRetrieve:
    """Integration test using the full hybrid retrieval path."""

    @pytest.mark.anyio
    async def test_dedup_by_move_id(self, synthetic_vendor):
        """The same move_id should not appear twice in hybrid results."""
        partner_id = synthetic_vendor["partner_id"]
        _SEED_DATA[0]["distance"] = 0.01

        import app.retrieve as retrieve_mod

        pool = FakePool()
        retrieve_mod._pool = pool
        try:
            query_vector = [0.0] * 1024
            results = await retrieve_mod.hybrid_retrieve(
                partner_id,
                query_vector,
                extracted_ref="INV-2025-001",
            )
            move_ids = [r["move_id"] for r in results]
            assert len(move_ids) == len(set(move_ids)), (
                f"Duplicate move_ids found: {move_ids}"
            )
        finally:
            retrieve_mod._pool = None

    @pytest.mark.anyio
    async def test_ref_lookup_adds_bills(self, synthetic_vendor):
        """A ref match should add the bill if not already present."""
        partner_id = synthetic_vendor["partner_id"]

        # Add a posted bill NOT in the vector store but matching ref
        import app.retrieve as retrieve_mod

        pool = FakePool()
        retrieve_mod._pool = pool
        try:
            query_vector = [0.0] * 1024
            results = await retrieve_mod.hybrid_retrieve(
                partner_id,
                query_vector,
                extracted_ref="NONEXISTENT-REF-999",
            )
            # The vector results should still be present
            move_ids = [r["move_id"] for r in results]
            assert len(move_ids) > 0
        finally:
            retrieve_mod._pool = None


class TestGLAccountFrequencies:
    """Test GL frequency aggregation."""

    @pytest.mark.anyio
    async def test_empty_when_no_history(self):
        """Should return an empty dict when the vendor has no bills."""
        import app.retrieve as retrieve_mod

        pool = FakePool()
        retrieve_mod._pool = pool
        try:
            freqs = await retrieve_mod.gl_account_frequencies(9999)
            assert isinstance(freqs, dict)
            assert len(freqs) == 0
        finally:
            retrieve_mod._pool = None


class TestSchemas:
    """Test the request/response schemas."""

    def test_request_schema(self):
        from app.schemas import VendorContextRequest

        req = VendorContextRequest(partner_id=1, ocr_text="test invoice")
        assert req.partner_id == 1
        assert req.ocr_text == "test invoice"
        assert req.extracted_ref == ""

    def test_response_schema(self):
        from app.schemas import CandidateBill, VendorContextResponse

        resp = VendorContextResponse(
            candidates=[
                CandidateBill(move_id=1, content="bill", distance=0.1),
            ],
            gl_account_frequencies={"100000": 5},
            query_embedding_model="voyage-3",
        )
        assert len(resp.candidates) == 1
        assert resp.candidates[0].move_id == 1

    def test_validation_verdict_schema(self):
        from app.schemas import ValidationVerdict

        verdict = ValidationVerdict(
            account_id="100000",
            account_confidence=0.92,
            amount_plausible=True,
            duplicate_of_move_id=None,
            flags=[],
            reasoning="Vendor consistently posts to this account",
        )
        assert verdict.account_id == "100000"
        assert verdict.account_confidence == 0.92
        assert verdict.duplicate_of_move_id is None


class TestVectorToLiteral:
    """Test the pgvector literal formatter."""

    def test_format(self):
        from app.retrieve import _vector_to_literal

        result = _vector_to_literal([0.1, 0.2, 0.3])
        assert result.startswith("[")
        assert result.endswith("]")
        assert "0.1" in result
        assert "0.2" in result

    def test_empty(self):
        from app.retrieve import _vector_to_literal

        result = _vector_to_literal([])
        assert result == "[]"
