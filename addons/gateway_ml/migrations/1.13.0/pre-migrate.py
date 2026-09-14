import logging

_logger = logging.getLogger(__name__)

_MODULE = "gateway_ml"

_RENAMED = {
    "integration.service": (
        ("service_claude", "service_anthropic"),
        ("service_gemini", "service_google"),
        ("service_gemini_openai", "service_google_openai"),
    ),
    "gateway.ml.provider": (
        ("ai_provider_claude", "ai_provider_anthropic"),
        ("ai_provider_gemini", "ai_provider_google"),
    ),
}


def migrate(cr, version):
    if not version:
        return

    renamed = 0
    for model, pairs in _RENAMED.items():
        for old, new in pairs:
            cr.execute(
                """
                UPDATE ir_model_data d
                   SET name = %(new)s
                 WHERE d.module = %(module)s
                   AND d.model = %(model)s
                   AND d.name = %(old)s
                   AND NOT EXISTS (
                         SELECT 1
                           FROM ir_model_data e
                          WHERE e.module = %(module)s
                            AND e.model = %(model)s
                            AND e.name = %(new)s
                       )
                """,
                {"module": _MODULE, "model": model, "old": old, "new": new},
            )
            if cr.rowcount:
                renamed += cr.rowcount
                _logger.info(
                    "gateway_ml 19.0.1.13.0: re-tagged %s %s -> %s",
                    model,
                    old,
                    new,
                )

    if renamed:
        _logger.info(
            "gateway_ml 19.0.1.13.0: carried %s external id(s) onto the vendor's "
            "company name, keeping their rows. Without this the data load reads "
            "each new id as a new record and INSERTs a second endpoint holding a "
            "code the unique index already has",
            renamed,
        )
