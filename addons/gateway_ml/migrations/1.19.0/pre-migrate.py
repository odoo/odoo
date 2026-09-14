import logging

from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)

_SEEDED = (
    ("ai_model_openai_gpt_5_6_luna", "ai_provider_openai", "gpt-5.6-luna"),
    ("ai_model_deepseek_flash", "ai_provider_deepseek", "deepseek-flash"),
    ("ai_model_groq_gpt_oss_120b", "ai_provider_groq", "openai/gpt-oss-120b"),
    ("ai_model_openai_gpt_transcribe", "ai_provider_openai", "gpt-transcribe"),
)


def migrate(cr, version):
    if not version:
        return

    if not column_exists(cr, "gateway_ml_model", "has_timestamps"):
        cr.execute("ALTER TABLE gateway_ml_model ADD COLUMN has_timestamps boolean")
        cr.execute(
            "UPDATE gateway_ml_model SET has_timestamps = TRUE "
            "WHERE kind = 'audio' AND code <> %s",
            ("gpt-transcribe",),
        )
        _logger.info(
            "gateway_ml 19.0.1.19.0: marked %s audio model(s) as returning "
            "timestamps; every one was already read through transcribe_cues, and "
            "speech_ai now picks only models that say so",
            cr.rowcount,
        )

    for xmlid, provider_xmlid, code in _SEEDED:
        cr.execute(
            """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            SELECT 'gateway_ml', %(xmlid)s::varchar, 'gateway.ml.model', m.id, TRUE
              FROM gateway_ml_model m
              JOIN ir_model_data p
                ON p.module = 'gateway_ml'
               AND p.name = %(provider_xmlid)s
               AND p.model = 'gateway.ml.provider'
               AND p.res_id = m.provider_id
             WHERE m.code = %(code)s
               AND NOT EXISTS (
                     SELECT 1
                       FROM ir_model_data d
                      WHERE d.module = 'gateway_ml'
                        AND d.name = %(xmlid)s
                   )
            """,
            {"xmlid": xmlid, "provider_xmlid": provider_xmlid, "code": code},
        )
        if cr.rowcount:
            _logger.info(
                "gateway_ml 19.0.1.19.0: an administrator had already added %s; its "
                "row now carries %s and keeps the values they set, instead of the "
                "data load inserting a second row the unique code index refuses",
                code,
                xmlid,
            )
