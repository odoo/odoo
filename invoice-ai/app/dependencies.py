"""FastAPI dependency providers.

`Depends(get_claude_service)` is the seam tests use to inject a fake Claude
service (patching `app.dependencies.get_claude_service`) — the equivalent of
the Odoo suite patching `anthropic.Anthropic`. `Depends(get_embedder)` is
the same seam for the Voyage embedder (`app/embeddings.py`).
"""

from .claude import ClaudeService, get_claude_service
from .embeddings import VoyageEmbedder, get_embedder

__all__ = [
    "ClaudeService",
    "get_claude_service",
    "VoyageEmbedder",
    "get_embedder",
]
