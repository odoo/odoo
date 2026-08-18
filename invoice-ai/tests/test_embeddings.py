"""Tests for the Voyage `voyage-3` embedder and `POST /v1/embed`.

Two layers:

1. **Embedder logic** (``app/embeddings.py``): batching, retry-once,
   dimension assertion — exercised with a fake Voyage client, never the SDK.
2. **Endpoint** (``app/main.py``): happy path returns aligned 1024-d
   vectors; empty texts -> 400; upstream failure -> 503 (E5032) with the
   same envelope the Odoo embed cron parses.

The endpoint tests override the embedder via ``app.dependency_overrides`` —
patching ``app.main.get_embedder`` by name does NOT work because FastAPI
captured the function object at import time (the same lesson documented in
``tests/conftest.py`` for ``get_claude_service``).
"""

import pytest

from app.embeddings import (
    VOYAGE_DIMENSIONS,
    VoyageEmbedder,
    VoyageEmbeddingError,
)


def _fake_vector(seed: float, dim: int = VOYAGE_DIMENSIONS) -> list[float]:
    return [(seed + index) / (dim * 100.0) for index in range(dim)]


class FakeVoyageResult:
    """Mirrors voyageai's Client.embed result: items with ``float_list``."""

    def __init__(self, vectors):
        self.embeddings = [type("Embedding", (), {"float_list": v}) for v in vectors]


class FakeVoyage:
    """Recording fake for voyageai.Client — never touches the network."""

    def __init__(self, vectors=None, fail_times: int = 0):
        self.vectors = vectors or [_fake_vector(i) for i in range(4)]
        self.fail_times = fail_times
        self.calls: list[dict] = []

    def embed(self, texts, *, model, input_type):
        self.calls.append({"texts": texts, "model": model, "input_type": input_type})
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ConnectionError("fake upstream connection error")
        return FakeVoyageResult(self.vectors[: len(texts)])


class TestVoyageEmbedder:
    def test_embed_documents_returns_aligned_vectors(self):
        fake = FakeVoyage()
        embedder = VoyageEmbedder(client=fake)
        vectors = embedder.embed_documents(["bill one", "bill two"])
        assert len(vectors) == 2
        assert all(len(v) == VOYAGE_DIMENSIONS for v in vectors)
        assert fake.calls[0]["model"] == "voyage-3"
        assert fake.calls[0]["input_type"] == "document"

    def test_embed_query_uses_query_input_type(self):
        fake = FakeVoyage()
        embedder = VoyageEmbedder(client=fake)
        vector = embedder.embed_query("search for ACME")
        assert len(vector) == VOYAGE_DIMENSIONS
        assert fake.calls[0]["input_type"] == "query"

    def test_large_batch_is_split(self):
        fake = FakeVoyage(vectors=[_fake_vector(i) for i in range(300)])
        embedder = VoyageEmbedder(client=fake)
        vectors = embedder.embed_documents([f"doc-{i}" for i in range(300)])
        assert len(vectors) == 300
        # 300 texts at VOYAGE_MAX_BATCH=128 -> ceil(300/128) = 3 calls
        assert len(fake.calls) == 3
        assert [len(call["texts"]) for call in fake.calls] == [128, 128, 44]

    def test_transient_failure_retries_once_then_succeeds(self):
        fake = FakeVoyage(fail_times=1)
        embedder = VoyageEmbedder(client=fake)
        vectors = embedder.embed_documents(["bill one"])
        assert len(vectors) == 1
        assert len(fake.calls) == 2  # first attempt failed, retry succeeded

    def test_retry_exhausted_raises_typed_error(self):
        fake = FakeVoyage(fail_times=99)
        embedder = VoyageEmbedder(client=fake)
        with pytest.raises(VoyageEmbeddingError):
            embedder.embed_documents(["bill one"])

    def test_wrong_dimension_is_rejected(self):
        fake = FakeVoyage(vectors=[[0.1, 0.2, 0.3]])  # 3-dim, not 1024
        embedder = VoyageEmbedder(client=fake)
        with pytest.raises(VoyageEmbeddingError):
            embedder.embed_documents(["bill one"])


# ---------------------------------------------------------------------------
# Endpoint — POST /v1/embed (JWT-protected)
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_headers() -> dict[str, str]:
    from tests.conftest import mint_token

    return {"Authorization": f"Bearer {mint_token()}"}


class TestEmbedEndpoint:
    @pytest.mark.anyio
    async def test_embed_happy_path(self, client, auth_headers):
        """Dependency override supplies a fake embedder — no network."""
        from app.dependencies import get_embedder
        from app.main import app as fastapi_app

        fake = FakeVoyage()
        fastapi_app.dependency_overrides[get_embedder] = lambda: VoyageEmbedder(
            client=fake,
        )
        try:
            response = await client.post(
                "/v1/embed",
                headers=auth_headers,
                json={"texts": ["ACME SUPPLIES LLC", "Global Freight Inc."]},
            )
            assert response.status_code == 200
            body = response.json()
            assert len(body["vectors"]) == 2
            assert all(len(v) == VOYAGE_DIMENSIONS for v in body["vectors"])
            assert body["model"] == "voyage-3"
            assert body["dimensions"] == VOYAGE_DIMENSIONS
        finally:
            fastapi_app.dependency_overrides.pop(get_embedder, None)

    @pytest.mark.anyio
    async def test_embed_empty_texts_returns_400(self, client, auth_headers):
        response = await client.post(
            "/v1/embed",
            headers=auth_headers,
            json={"texts": []},
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "E4001"

    @pytest.mark.anyio
    async def test_embed_upstream_failure_maps_to_503(self, client, auth_headers):
        from app.dependencies import get_embedder
        from app.main import app as fastapi_app

        class RaisingEmbedder(VoyageEmbedder):
            def embed_documents(self, texts):
                raise VoyageEmbeddingError("upstream down")

        fastapi_app.dependency_overrides[get_embedder] = lambda: RaisingEmbedder()
        try:
            response = await client.post(
                "/v1/embed",
                headers=auth_headers,
                json={"texts": ["ACME SUPPLIES LLC"]},
            )
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "E5032"
        finally:
            fastapi_app.dependency_overrides.pop(get_embedder, None)
