_STRUCTURED_OUTPUT = {
    "ai_model_openai_gpt_5_6_luna": "json_schema",
    "ai_model_groq_gpt_oss_120b": "json_schema",
    "ai_model_deepseek_flash": "json_object",
    "ai_model_moonshot_kimi_k3": "json_object",
}


def migrate(cr, version):
    if not version:
        return
    for xmlid, mode in _STRUCTURED_OUTPUT.items():
        cr.execute(
            """
            UPDATE gateway_ml_model m
               SET structured_output = %s
              FROM ir_model_data d
             WHERE d.module = 'gateway_ml' AND d.name = %s AND d.res_id = m.id
               AND m.structured_output = 'prompted'
            """,
            (mode, xmlid),
        )
