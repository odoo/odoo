from .openai_compatible import OpenAICompatibleClient


class GroqClient(OpenAICompatibleClient):
    ENDPOINT_CODE = "groq"

    MAX_TOKENS_LIMIT = 65536


class MoonshotClient(OpenAICompatibleClient):
    ENDPOINT_CODE = "moonshot"

    MIN_TEMPERATURE = 1.0
    MAX_TEMPERATURE = 1.0
    MAX_TOKENS_LIMIT = 1048576


def get_groq_client(env, company_id=None):
    return GroqClient(env, company_id)


def get_moonshot_client(env, company_id=None):
    return MoonshotClient(env, company_id)
