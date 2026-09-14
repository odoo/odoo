import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

QUIRKS = {
    "ai_model_claude_sonnet_5": {"sampling_params": False},
    "ai_model_openai_gpt_5_6_luna": {
        "max_tokens_param": "max_completion_tokens",
        "request_extra": {"reasoning_effort": "none"},
    },
    "ai_model_openai_gpt_transcribe": {"language_form_key": "languages[]"},
    "ai_model_gemini_3_5_flash_lite": {
        "min_max_tokens": 2000,
        "request_extra": {"reasoning_effort": "low"},
    },
    "ai_model_deepseek_flash": {"request_extra": {"thinking": {"type": "disabled"}}},
    "ai_model_deepgram_nova_3": {"vocabulary_param": "keyterm"},
    "ai_model_groq_gpt_oss_120b": {"request_extra": {"reasoning_effort": "low"}},
    "ai_model_moonshot_kimi_k3": {
        "min_max_tokens": 2000,
        "request_extra": {"temperature": 1},
    },
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    for xmlid, values in QUIRKS.items():
        model = env.ref(f"gateway_ml.{xmlid}", raise_if_not_found=False)
        if not model:
            continue
        defaults = model.default_get(list(values))
        untouched = {
            name: value
            for name, value in values.items()
            if model[name] == defaults.get(name, False) or not model[name]
        }
        if untouched:
            model.write(untouched)
            _logger.info("gateway_ml: %s now carries %s", model.code, sorted(untouched))
