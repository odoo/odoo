import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    rules = env["automation.rule"].search(
        [("trigger", "=", "on_webhook"), ("auth_type", "=", "none")]
    )
    if not rules:
        return
    rules.write({"auth_type": "hmac_sha256"})
    rules._start_webhook_audit_window()
    for rule in rules:
        _logger.warning(
            "automation_webhook: rule %s (%s) authenticated nothing; it now has an "
            "HMAC-SHA256 secret and runs unsigned calls only until %s, then refuses "
            "them. Give its sender the secret.",
            rule.id,
            rule.name,
            rule.webhook_enforce_from,
        )
