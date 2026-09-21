import logging

_logger = logging.getLogger(__name__)

# The vendors' stated request-body limits, in MiB; the data file is noupdate so
# an existing database takes them here.
_LIMITS = {
    "ai_model_openai_gpt_transcribe": 25,
    "ai_model_openai_whisper_1": 25,
    "ai_model_gemini_flash_lite_latest": 20,
    "ai_model_deepgram_nova_3": 2048,
    "ai_model_groq_whisper_large_v3_turbo": 25,
}


def migrate(cr, version):
    if not version:
        return
    for xmlid, limit in _LIMITS.items():
        cr.execute(
            """
            UPDATE gateway_ml_model m
               SET max_audio_mb = %s
              FROM ir_model_data d
             WHERE d.module = 'gateway_ml' AND d.name = %s AND d.res_id = m.id
               AND COALESCE(m.max_audio_mb, 0) = 0
            """,
            (limit, xmlid),
        )
        if cr.rowcount:
            _logger.info(
                "gateway_ml 19.0.1.22.0: %s accepts up to %s MiB of audio", xmlid, limit
            )
