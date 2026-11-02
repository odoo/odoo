import logging

from .data.approval_sources import APPROVAL_SOURCES

_logger = logging.getLogger(__name__)


def _od19_step_values(env, model_name, step):
    approver_field = step.get("approver_field") or ""
    if approver_field and approver_field not in env[model_name]._fields:
        _logger.warning(
            "Approval Center: %s.%s missing -> shared pool step",
            model_name, approver_field,
        )
        approver_field = ""
    return {
        "sequence": step.get("sequence", 10),
        "label": step["label"],
        "state_field": step.get("state_field", "state"),
        "state_value": step["state_value"],
        "approver_field": approver_field,
        "approver_kind": step.get("approver_kind", "user"),
    }


def _od19_source_values(env, spec, model_id, model_name):
    model_fields = env[model_name]._fields
    requester_field = spec.get("requester_field") or "create_uid"
    if requester_field not in model_fields:
        requester_field = "create_uid"
    submitted_field = spec.get("submitted_date_field") or "create_date"
    if submitted_field not in model_fields:
        submitted_field = "create_date"
    return {
        "name": spec["name"],
        "model_id": model_id,
        "icon": spec.get("icon", "fa-inbox"),
        "action_xmlid": spec.get("action_xmlid"),
        "sequence": spec.get("sequence", 10),
        "requester_field": requester_field,
        "requester_kind": spec.get("requester_kind", "user"),
        "submitted_date_field": submitted_field,
        "rejected_states": spec.get("rejected_states"),
        "success_states": spec.get("success_states"),
        "strategy": spec.get("strategy", "field"),
        "sla_days": spec.get("sla_days", 0),
        "step_ids": [
            (0, 0, _od19_step_values(env, model_name, step))
            for step in spec.get("steps", [])
        ],
    }


def post_init_hook(env):
    """Seed Approval Center sources (idempotent, install only)."""
    Source = env["od19.approval.source"]
    IrModel = env["ir.model"]
    for spec in APPROVAL_SOURCES:
        model_name = spec.get("model")
        if not model_name or model_name not in env:
            _logger.info("Approval Center: skip %s (not installed)", model_name)
            continue
        model = IrModel._get(model_name)
        if not model:
            continue
        if Source.with_context(active_test=False).search([
            ("model_id", "=", model.id),
            ("name", "=", spec["name"]),
        ], limit=1):
            continue
        Source.create(_od19_source_values(env, spec, model.id, model_name))
        _logger.info("Approval Center: seeded %s (%s)", spec["name"], model_name)
