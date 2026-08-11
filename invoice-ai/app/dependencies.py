"""FastAPI dependency providers.

`Depends(get_claude_service)` is the seam tests use to inject a fake Claude
service (patching `app.dependencies.get_claude_service`) — the equivalent of
the Odoo suite patching `anthropic.Anthropic`.
"""

from .claude import ClaudeService, get_claude_service

__all__ = ["ClaudeService", "get_claude_service"]
