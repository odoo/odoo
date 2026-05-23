import logging
import time
from collections import defaultdict
from threading import Lock

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)

MAX_PROMPT_CHARS = 8000
MAX_HISTORY_TURNS = 10
RATE_LIMIT_WINDOW_SEC = 60
RATE_LIMIT_MAX_CALLS = 20

_rate_limit_lock = Lock()
_rate_limit_state: dict[int, list[float]] = defaultdict(list)


def _check_authorized(env):
    """Only project-manager (or admin) can spend org LLM budget."""
    if env.user._is_admin():
        return
    if not env.user.has_group("project.group_project_manager"):
        msg = "Solar AI: this endpoint requires the Project Manager group."
        raise AccessError(msg)


def _check_rate_limit(user_id):
    """Sliding window rate limit per user."""
    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SEC
    with _rate_limit_lock:
        calls = _rate_limit_state[user_id]
        calls[:] = [t for t in calls if t > cutoff]
        if len(calls) >= RATE_LIMIT_MAX_CALLS:
            return False
        calls.append(now)
    return True


class SolarAiOlgProxy(http.Controller):
    """Emulates Odoo's OLG API endpoint so the html_editor 'Translate with AI'
    and 'Generate with ChatGPT' buttons route to OpenRouter instead of Odoo SA.

    Hardened: authorization (project manager group), per-user rate limit,
    prompt-length caps, and bounded conversation history to prevent budget abuse.
    """

    def _build_messages(self, prompt, history):
        prompt = (prompt or "")[:MAX_PROMPT_CHARS]
        history = (history or [])[-MAX_HISTORY_TURNS:]
        messages = []
        for turn in history:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            content = (turn.get("content") or "")[:MAX_PROMPT_CHARS]
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})
        return messages

    @http.route(
        "/solar_ai/olg/api/olg/1/chat",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def olg_chat(self, **kwargs):
        _check_authorized(request.env)
        if not _check_rate_limit(request.env.user.id):
            _logger.warning(
                "solar_ai: rate limit hit for user %s on /chat",
                request.env.user.id,
            )
            return {"status": "error", "error": "rate_limited"}

        body = request.get_json_data()
        prompt = body.get("prompt", "")
        history = body.get("conversation_history", [])
        messages = self._build_messages(prompt, history)

        service = request.env["solar.ai.service"]
        result = service.chat(messages)

        if result.get("error"):
            return {"status": "error", "error": result["error"]}
        return {"status": "success", "content": result["content"]}

    @http.route(
        "/solar_ai/olg/api/olg/1/generate_placeholder",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def olg_generate_placeholder(self, **kwargs):
        _check_authorized(request.env)
        if not _check_rate_limit(request.env.user.id):
            _logger.warning(
                "solar_ai: rate limit hit for user %s on /generate_placeholder",
                request.env.user.id,
            )
            return {"status": "error", "error": "rate_limited"}

        body = request.get_json_data()
        prompt = body.get(
            "prompt",
            "Generate a professional website text for a solar energy company.",
        )[:MAX_PROMPT_CHARS]

        service = request.env["solar.ai.service"]
        result = service.chat([{"role": "user", "content": prompt}])

        if result.get("error"):
            return {"status": "error", "error": result["error"]}
        return {"status": "success", "content": result["content"]}
