from odoo import fields, models


class SuiteDashboardProviderRegistry(models.Model):
    _name = "suite.dashboard.provider.registry"
    _description = "Suite Dashboard Provider Registry"
    _order = "name, id"

    name = fields.Char(required=True)
    key = fields.Char(required=True, index=True)
    provider_model = fields.Char(required=True)
    bridge_module = fields.Char()
    active = fields.Boolean(default=True)

    _key_uniq = models.Constraint(
        "UNIQUE (key)",
        "The provider key must be unique.",
    )
