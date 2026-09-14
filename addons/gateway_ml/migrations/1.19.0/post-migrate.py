import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_CORRECTED_SEEDS = (
    (
        "ai_model_moonshot_kimi_k3",
        {
            "max_context_window": 131072,
            "max_output_tokens": 32768,
            "cost_per_1m_input": 0,
            "cost_per_1m_output": 0,
        },
        {
            "max_context_window": 1048576,
            "max_output_tokens": 1048576,
            "cost_per_1m_input": 3.00,
            "cost_per_1m_output": 15.00,
        },
    ),
    (
        "ai_model_gemini_3_5_flash_lite",
        {
            "max_context_window": 0,
            "max_output_tokens": 0,
            "cost_per_1m_input": 0,
            "cost_per_1m_output": 0,
        },
        {
            "max_context_window": 1048576,
            "max_output_tokens": 65536,
            "cost_per_1m_input": 0.30,
            "cost_per_1m_output": 2.50,
        },
    ),
    (
        "ai_model_openai_whisper_1",
        {"cost_per_audio_minute": 0},
        {"cost_per_audio_minute": 0.006},
    ),
    (
        "ai_model_groq_whisper_large_v3_turbo",
        {"cost_per_audio_minute": 0},
        {"cost_per_audio_minute": 0.000667},
    ),
)

# The vendor shut these ids down (DeepSeek 2026-07-24, Groq 2026-08-16 and
# 2026-07-17) or the catalog moved off them (gpt-4o-mini). Scout has no successor:
# Groq serves no production vision model.
_REPLACED_SEEDS = (
    ("ai_model_openai_gpt_4o_mini", "ai_model_openai_gpt_5_6_luna"),
    ("ai_model_deepseek_chat", "ai_model_deepseek_flash"),
    ("ai_model_groq_llama_3_3_70b", "ai_model_groq_gpt_oss_120b"),
    ("ai_model_groq_llama_4_scout", None),
)


def migrate(cr, version):
    if not version:
        return
    _correct_seeds(cr)
    env = api.Environment(cr, SUPERUSER_ID, {})
    for old_xmlid, new_xmlid in _REPLACED_SEEDS:
        _retire_seed(env, old_xmlid, new_xmlid)
    env.flush_all()


def _correct_seeds(cr):
    for xmlid, seeded, corrected in _CORRECTED_SEEDS:
        assignments = ", ".join(f"{column} = %({column})s" for column in corrected)
        still_seeded = " AND ".join(
            f"COALESCE(m.{column}, 0) = %(seeded_{column})s" for column in seeded
        )
        cr.execute(
            f"""
            UPDATE gateway_ml_model m
               SET {assignments}
              FROM ir_model_data d
             WHERE d.module = 'gateway_ml'
               AND d.name = %(xmlid)s
               AND d.model = 'gateway.ml.model'
               AND d.res_id = m.id
               AND {still_seeded}
            """,
            {
                "xmlid": xmlid,
                **corrected,
                **{f"seeded_{column}": value for column, value in seeded.items()},
            },
        )
        _logger.info(
            "gateway_ml 19.0.1.19.0: %s %s",
            xmlid,
            f"corrected to {corrected}"
            if cr.rowcount
            else "no longer carries its seeded values, so it was left as an "
            "administrator set it",
        )


def _retire_seed(env, old_xmlid, new_xmlid):
    old = env.ref(f"gateway_ml.{old_xmlid}", raise_if_not_found=False)
    if not old:
        return
    new = new_xmlid and env.ref(f"gateway_ml.{new_xmlid}", raise_if_not_found=False)
    moved_providers = env["gateway.ml.provider"]
    if new:
        moved_providers = env["gateway.ml.provider"].search([("default_model_id", "=", old.id)])
        moved_providers.write({"default_model_id": new.id})
        _carry_hops(env, old, new)
    if env["gateway.ml.provider"].search_count([("default_model_id", "=", old.id)]):
        _logger.info(
            "gateway_ml 19.0.1.19.0: %s is still a provider's default and has no "
            "replacement, so it stays active",
            old.code,
        )
        return
    old.active = False
    _logger.info(
        "gateway_ml 19.0.1.19.0: archived %s; %s provider(s) moved to %s",
        old.code,
        len(moved_providers),
        new.code if new else "nothing",
    )


def _carry_hops(env, old, new):
    Hop = env["gateway.ml.model.fallback"]
    for hop in Hop.search([("fallback_id", "=", old.id)]):
        if hop.model_id == new or Hop.search_count(
            [("model_id", "=", hop.model_id.id), ("fallback_id", "=", new.id)]
        ):
            hop.unlink()
        else:
            hop.fallback_id = new
    for hop in Hop.search([("model_id", "=", old.id)]):
        if hop.fallback_id == new or Hop.search_count(
            [("model_id", "=", new.id), ("fallback_id", "=", hop.fallback_id.id)]
        ):
            hop.unlink()
        else:
            hop.model_id = new
