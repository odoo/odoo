import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SuiteDashboardTemplate(models.Model):
    _name = "suite.dashboard.template"
    _description = "Dashboard Template"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    provider_key = fields.Char(required=True, index=True)
    description = fields.Text()
    item_definition_json = fields.Text(default="[]")
    default_filter_state = fields.Text(
        help="JSON payload with the default filters for workspaces created from this template."
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "UNIQUE (code)",
        "Template code must be unique.",
    )

    @api.constrains("item_definition_json")
    def _check_item_definition_json(self):
        for rec in self:
            if not isinstance(rec._get_item_definitions(), list):
                raise ValidationError("Template widget definition must be a JSON list.")

    def _get_item_definitions(self):
        self.ensure_one()
        raw = (self.item_definition_json or "").strip() or "[]"
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError("Invalid template widget JSON.") from exc
