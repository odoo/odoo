import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT 1 FROM ir_module_module WHERE name = 'integration' AND state = %s",
        ("installed",),
    )
    if cr.fetchone():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env["ir.module.module"].search(
            [("name", "=", "automation_webhook"), ("state", "=", "uninstalled")]
        ).button_install()
        return
    cr.execute(
        """
        UPDATE automation_rule
           SET trigger = 'on_hand', active = false
         WHERE trigger = 'on_webhook'
     RETURNING id, name->>'en_US'
        """
    )
    archived = cr.fetchall()
    if archived:
        _logger.warning(
            "automation: webhooks moved to automation_webhook, which needs "
            "integration; this database has none, so %s webhook rule(s) were "
            "archived and set to manual trigger: %s",
            len(archived),
            ", ".join(f"#{rule_id} {name}" for rule_id, name in archived),
        )
