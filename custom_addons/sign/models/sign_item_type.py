from odoo import fields, models


class SignItemType(models.Model):
    _name = "sign.item.type"
    _description = "Sign Item Type"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    requires_options = fields.Boolean(default=False)

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "Sign item type code must be unique.",
    )
