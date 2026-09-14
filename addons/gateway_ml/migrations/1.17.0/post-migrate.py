import logging

_logger = logging.getLogger(__name__)

_CORRECTED_SEEDS = (
    (
        "ai_model_openai_gpt_4o_mini",
        {
            "cost_per_1m_input": 2.50,
            "cost_per_1m_output": 10.00,
            "cost_per_1m_image": 2.125,
        },
        {
            "cost_per_1m_input": 0.15,
            "cost_per_1m_output": 0.60,
            "cost_per_1m_image": 0.0,
        },
    ),
    (
        "ai_model_claude_sonnet_5",
        {
            "cost_per_1m_input": 3.00,
            "cost_per_1m_output": 15.00,
            "cost_per_1m_image": 4.80,
            "max_output_tokens": 8192,
        },
        {
            "cost_per_1m_input": 2.00,
            "cost_per_1m_output": 10.00,
            "cost_per_1m_image": 0.0,
            "max_output_tokens": 128000,
        },
    ),
)


def migrate(cr, version):
    if not version:
        return

    for xmlid, seeded, corrected in _CORRECTED_SEEDS:
        assignments = ", ".join(f"{column} = %({column})s" for column in corrected)
        still_seeded = " AND ".join(
            f"m.{column} = %(seeded_{column})s" for column in seeded
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
        if cr.rowcount:
            _logger.info(
                "gateway_ml 19.0.1.17.0: %s still carried the wrong seeded price and "
                "output cap; corrected to %s",
                xmlid,
                corrected,
            )
        else:
            _logger.info(
                "gateway_ml 19.0.1.17.0: %s no longer carries the seeded %s, so it was "
                "left as an administrator set it",
                xmlid,
                seeded,
            )
