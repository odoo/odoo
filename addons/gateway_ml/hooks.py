import logging

_logger = logging.getLogger(__name__)

_OLD_MODULE = "api_gateway"
_NEW_MODULE = "gateway_ml"

_MOVED_RECORDS = {
    "integration.service": [
        "service_anthropic",
        "service_deepseek",
        "service_openai",
        "service_google",
        "service_deepgram",
    ],
    "gateway.ml.provider": [
        "ai_provider_google",
        "ai_provider_anthropic",
        "ai_provider_openai",
        "ai_provider_deepseek",
    ],
    "ai.use.case.tag": [
        "tag_vision",
        "tag_reasoning",
        "tag_speed",
        "tag_budget",
        "tag_accuracy",
        "tag_long_context",
        "tag_ocr",
        "tag_embeddings",
        "tag_chat",
        "tag_content_generation",
        "tag_audio",
    ],
    "ir.ui.view": [
        "view_ai_provider_search",
        "view_ai_provider_list",
        "view_ai_provider_kanban",
        "view_ai_provider_form",
        "view_ai_use_case_tag_list",
        "view_ai_use_case_tag_form",
        "view_ai_use_case_tag_search",
    ],
    "ir.actions.act_window": [
        "action_ai_provider",
        "action_ai_use_case_tag",
    ],
    "ir.model.access": [
        "access_ai_provider_user",
        "access_ai_provider_admin",
        "access_ai_provider_system",
        "access_ai_use_case_tag_user",
        "access_ai_use_case_tag_admin",
        "access_ai_use_case_tag_system",
    ],
}


# Two records were renamed by the split, not just moved: api_gateway named them
# after the model ("claude", "gemini"), gateway_ml names them after the vendor
# ("anthropic", "google"). _retag_moved_records matches on name and only changes
# the module, so without this pass it silently skips both -- and the data load
# then inserts a second row, which integration_service_code_unique rejects
# because the code ("claude", "gemini") did not change.
_RENAMED_RECORDS = {
    "integration.service": {
        "service_claude": "service_anthropic",
        "service_gemini": "service_google",
    },
    "gateway.ml.provider": {
        "ai_provider_claude": "ai_provider_anthropic",
        "ai_provider_gemini": "ai_provider_google",
    },
}


def _rename_moved_records(env):
    renamed = 0
    for model, mapping in _RENAMED_RECORDS.items():
        for old_name, new_name in mapping.items():
            env.cr.execute(
                """
                UPDATE ir_model_data d
                   SET module = %(new_mod)s, name = %(new_name)s
                 WHERE d.module = %(old_mod)s
                   AND d.model = %(model)s
                   AND d.name = %(old_name)s
                   AND NOT EXISTS (
                         SELECT 1 FROM ir_model_data e
                          WHERE e.module = %(new_mod)s
                            AND e.model = %(model)s
                            AND e.name = %(new_name)s
                       )
                """,
                {
                    "new_mod": _NEW_MODULE,
                    "old_mod": _OLD_MODULE,
                    "model": model,
                    "old_name": old_name,
                    "new_name": new_name,
                },
            )
            if env.cr.rowcount:
                renamed += env.cr.rowcount
                _logger.info(
                    "gateway_ml: %s.%s -> %s.%s (%s)",
                    _OLD_MODULE,
                    old_name,
                    _NEW_MODULE,
                    new_name,
                    model,
                )
    return renamed


def _retag_moved_records(env):
    retagged = 0
    for model, names in _MOVED_RECORDS.items():
        env.cr.execute(
            """
            UPDATE ir_model_data d
               SET module = %(new)s
             WHERE d.module = %(old)s
               AND d.model = %(model)s
               AND d.name = ANY(%(names)s)
               AND NOT EXISTS (
                     SELECT 1
                       FROM ir_model_data e
                      WHERE e.module = %(new)s
                        AND e.name = d.name
                        AND e.model = d.model
                   )
            """,
            {
                "new": _NEW_MODULE,
                "old": _OLD_MODULE,
                "model": model,
                "names": names,
            },
        )
        if env.cr.rowcount:
            retagged += env.cr.rowcount
            _logger.info(
                "gateway_ml: re-tagged %s %s record(s) from %s",
                env.cr.rowcount,
                model,
                _OLD_MODULE,
            )
    if retagged:
        _logger.info(
            "gateway_ml: took ownership of %s record(s) from %s, preserving their ids "
            "so the data load updates in place and views keep their identity",
            retagged,
            _OLD_MODULE,
        )


def pre_init_hook(env):
    # Rename first: _retag_moved_records looks the records up by their new name.
    _rename_moved_records(env)
    _retag_moved_records(env)
