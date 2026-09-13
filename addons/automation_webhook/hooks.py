import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

_PREVIOUS_OWNER = "automation"

_WEBHOOK_FIELDS = ("url", "webhook_uuid", "record_getter", "log_webhook_calls")

_ADOPTED_RECORDS = (
    "selection__automation_rule__trigger__on_webhook",
    "model_inherit__automation_rule__mixin_inbound_gate",
)


def adopt_from_automation(env: api.Environment) -> int:
    gate_fields = set(env["mixin.inbound.gate"]._fields) - set(models.MAGIC_COLUMNS)
    gate_fields.discard("display_name")
    names = [
        f"field_automation_rule__{name}"
        for name in sorted(gate_fields.union(_WEBHOOK_FIELDS))
    ]
    names.extend(_ADOPTED_RECORDS)
    cr = env.cr
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'automation_webhook'
           AND name = ANY(%s)
           AND EXISTS (
               SELECT 1 FROM ir_model_data previous
                WHERE previous.module = %s AND previous.name = ir_model_data.name
           )
        """,
        (names, _PREVIOUS_OWNER),
    )
    cr.execute(
        """
        UPDATE ir_model_data SET module = 'automation_webhook'
         WHERE module = %s AND name = ANY(%s)
        """,
        (_PREVIOUS_OWNER, names),
    )
    adopted = cr.rowcount
    if adopted:
        _logger.info(
            "automation_webhook: adopted %s record(s) from %s", adopted, _PREVIOUS_OWNER
        )
    return adopted


def pre_init_hook(env: api.Environment) -> None:
    adopt_from_automation(env)
