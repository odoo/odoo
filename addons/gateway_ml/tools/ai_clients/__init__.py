from .base import BaseAIClient
from .claude import ClaudeClient, get_claude_client
from .deepgram import DeepgramClient
from .gemini import GeminiClient
from .openai_compatible import OpenAICompatibleClient

WIRE_CLIENTS = {
    "openai_compatible": OpenAICompatibleClient,
    "anthropic_messages": ClaudeClient,
    "gemini_native": GeminiClient,
    "deepgram": DeepgramClient,
}


def get_client_class(provider):
    own = provider.sudo().service_ids.filtered(
        lambda row: row.service_id == provider.endpoint_id
    )
    chosen = own.filtered(lambda row: row.operation == "chat") or own
    return WIRE_CLIENTS.get(chosen[:1].wire)


def get_ai_client(env, code, company_id=None):
    provider = env["gateway.ml.provider"].sudo().search([("code", "=", code)], limit=1)
    client_cls = provider and get_client_class(provider)
    if not client_cls:
        return None
    return client_cls(env, company_id=company_id, endpoint_code=code)


__all__ = [
    "WIRE_CLIENTS",
    "BaseAIClient",
    "ClaudeClient",
    "DeepgramClient",
    "GeminiClient",
    "OpenAICompatibleClient",
    "get_ai_client",
    "get_claude_client",
    "get_client_class",
]
