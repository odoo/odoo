import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SolarAiOlgProxy(http.Controller):
    """Emulates Odoo's OLG API endpoint so the html_editor 'Translate with AI'
    and 'Generate with ChatGPT' buttons route to OpenRouter instead of Odoo SA.
    """

    @http.route(
        "/solar_ai/olg/api/olg/1/chat",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def olg_chat(self, **kwargs):
        body = request.get_json_data()
        prompt = body.get("prompt", "")
        history = body.get("conversation_history", [])

        messages = []
        for turn in history:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": turn.get("content", "")})
        messages.append({"role": "user", "content": prompt})

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
        body = request.get_json_data()
        prompt = body.get(
            "prompt",
            "Generate a professional website text for a solar energy company.",
        )

        service = request.env["solar.ai.service"]
        result = service.chat([{"role": "user", "content": prompt}])

        if result.get("error"):
            return {"status": "error", "error": result["error"]}
        return {"status": "success", "content": result["content"]}
