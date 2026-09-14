import logging

from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)

_MOVED_COLUMNS = (
    "cost_per_1m_input",
    "cost_per_1m_output",
    "cost_per_1m_image",
    "cost_per_audio_minute",
    "max_context_window",
    "max_output_tokens",
    "supports_streaming",
    "supports_function_calling",
    "accuracy_rating",
    "speed_rating",
)

_BLIND_DEFAULT_MODELS = ("llama-3.3-70b-versatile",)


def migrate(cr, version):
    if not version:
        return

    if not column_exists(cr, "gateway_ml_provider", "default_model"):
        _logger.info(
            "gateway_ml 19.0.1.13.0: gateway_ml_provider.default_model is already gone; "
            "nothing to move"
        )
        return

    movable = [
        column for column in _MOVED_COLUMNS if column_exists(cr, "gateway_ml_provider", column)
    ]
    assignments = ", ".join(f"{column} = p.{column}" for column in movable)

    cr.execute(
        f"""
        UPDATE gateway_ml_model m
           SET {assignments}
          FROM gateway_ml_provider p
         WHERE m.provider_id = p.id
           AND m.code = p.default_model
        """
        if movable
        else "SELECT 0 WHERE FALSE"
    )
    copied = cr.rowcount

    cr.execute(
        """
        UPDATE gateway_ml_provider p
           SET default_model_id = m.id
          FROM gateway_ml_model m
         WHERE m.provider_id = p.id
           AND m.code = p.default_model
           AND p.default_model_id IS DISTINCT FROM m.id
        """
    )
    linked = cr.rowcount

    cr.execute(
        """
        SELECT p.id, p.default_model, e.code
          FROM gateway_ml_provider p
          JOIN integration_service e ON e.id = p.endpoint_id
         WHERE p.default_model IS NOT NULL
           AND p.default_model <> ''
           AND p.default_model_id IS NULL
        """
    )
    orphans = cr.fetchall()

    for provider_id, default_model, endpoint_code in orphans:
        columns = ", ".join(movable)
        sources = ", ".join(f"p.{column}" for column in movable)
        cr.execute(
            f"""
            INSERT INTO gateway_ml_model (
                provider_id, name, code, kind, sequence, active, has_vision
                {", " + columns if movable else ""}
            )
            SELECT p.id,
                   jsonb_build_object('en_US', %(code)s::text),
                   %(code)s::text,
                   'chat',
                   10,
                   TRUE,
                   CASE WHEN %(code)s::text = ANY(%(blind)s::text[]) THEN FALSE
                        ELSE COALESCE(p.has_vision, FALSE) END
                   {", " + sources if movable else ""}
              FROM gateway_ml_provider p
             WHERE p.id = %(provider_id)s
            RETURNING id
            """,
            {
                "code": default_model,
                "provider_id": provider_id,
                "blind": list(_BLIND_DEFAULT_MODELS),
            },
        )
        model_id = cr.fetchone()[0]
        cr.execute(
            "UPDATE gateway_ml_provider SET default_model_id = %s WHERE id = %s",
            (model_id, provider_id),
        )
        _logger.info(
            "gateway_ml 19.0.1.13.0: %s ran %r, which no seeded model describes. "
            "Created a gateway.ml.model row for it carrying the provider's values -- "
            "that is an administrator's choice, not the stale seed",
            endpoint_code,
            default_model,
        )

    cr.execute(
        """
        UPDATE gateway_ml_provider p
           SET has_vision = COALESCE(
                   (SELECT bool_or(m.has_vision)
                      FROM gateway_ml_model m
                     WHERE m.provider_id = p.id AND m.active), FALSE),
               has_audio = COALESCE(
                   (SELECT bool_or(m.kind = 'audio')
                      FROM gateway_ml_model m
                     WHERE m.provider_id = p.id AND m.active), FALSE)
        """
    )

    cr.execute(
        """
        SELECT e.code, p.available_models
          FROM gateway_ml_provider p
          JOIN integration_service e ON e.id = p.endpoint_id
         WHERE p.available_models IS NOT NULL
           AND p.available_models <> ''
        """
    )
    for endpoint_code, listed in cr.fetchall():
        _logger.info(
            "gateway_ml 19.0.1.13.0: %s.available_models said %r. The column is no "
            "longer a field; those names were never measured, so no gateway.ml.model "
            "row asserts a price for them. Add rows for the ones you run",
            endpoint_code,
            listed,
        )

    _logger.info(
        "gateway_ml 19.0.1.13.0: copied %s seeded model row(s) from their provider, "
        "linked %s default(s), rescued %s overridden default(s), and recomputed "
        "the capability roll-ups",
        copied,
        linked,
        len(orphans),
    )
