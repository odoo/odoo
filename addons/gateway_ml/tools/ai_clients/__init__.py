from .base import BaseAIClient
from .claude import ClaudeClient, get_claude_client
from .deepgram import DeepgramClient, get_deepgram_client
from .deepseek import DeepSeekClient, get_deepseek_client
from .gemini import GeminiClient, get_gemini_client
from .openai import OpenAIClient, get_openai_client
from .openai_wire_vendors import (
    GroqClient,
    MoonshotClient,
    get_groq_client,
    get_moonshot_client,
)

AI_CLIENT_REGISTRY = {}


def register_ai_client(code, client_cls):
    if not (isinstance(client_cls, type) and issubclass(client_cls, BaseAIClient)):
        raise TypeError(
            f"{client_cls!r} must be a BaseAIClient subclass to serve provider {code!r}",
        )
    AI_CLIENT_REGISTRY[code] = client_cls


def get_ai_client(env, code, company_id=None):
    client_cls = AI_CLIENT_REGISTRY.get(code)
    if client_cls is None:
        return None
    return client_cls(env, company_id=company_id)


for _cls in (
    ClaudeClient,
    DeepSeekClient,
    OpenAIClient,
    GeminiClient,
    DeepgramClient,
    GroqClient,
    MoonshotClient,
):
    register_ai_client(_cls.ENDPOINT_CODE, _cls)
del _cls


__all__ = [
    "AI_CLIENT_REGISTRY",
    "BaseAIClient",
    "ClaudeClient",
    "DeepSeekClient",
    "DeepgramClient",
    "GeminiClient",
    "GroqClient",
    "MoonshotClient",
    "OpenAIClient",
    "get_ai_client",
    "get_claude_client",
    "get_deepgram_client",
    "get_deepseek_client",
    "get_gemini_client",
    "get_groq_client",
    "get_moonshot_client",
    "get_openai_client",
    "register_ai_client",
]
