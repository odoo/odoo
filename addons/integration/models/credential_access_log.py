import logging
from typing import Any

from odoo import fields, models

_logger = logging.getLogger(__name__)


class CredentialAccessLog(models.Model):
    _inherit = "credential.access.log"

    service_name = fields.Char(
        related="credential_id.endpoint_id.name",
        string="Service",
        store=False,
        help="Name of the API service (if credential is linked to one)",
    )
    field_accessed = fields.Char(
        help="Which credential field was accessed (api_key, bearer_token, etc.)"
    )
    success = fields.Boolean(
        default=True,
        help="Whether the access was successful",
    )
    failure_reason = fields.Char(help="Reason for access failure (if applicable)")

    def action_view_related_logs(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": "Related Access Logs",
            "type": "ir.actions.act_window",
            "res_model": "credential.access.log",
            "view_mode": "list,form",
            "domain": [("credential_id", "=", self.credential_id.id)],
        }

    def action_view_security_report(self) -> dict[str, Any]:
        return {
            "name": "Credential Access Security Report",
            "type": "ir.actions.act_window",
            "res_model": "credential.access.log",
            "view_mode": "graph,pivot,list",
            "domain": [("credential_id.endpoint_id", "!=", False)],
            "context": {
                "search_default_failed_access": 1,
                "search_default_last_30_days": 1,
            },
        }
