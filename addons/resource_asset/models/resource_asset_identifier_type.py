import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResourceAssetIdentifierType(models.Model):
    _name = "resource.asset.identifier.type"
    _description = "Asset Identifier Type"
    _order = "sequence, name, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    pattern = fields.Char(
        help="Regular expression the normalized value must match in full. Empty accepts anything."
    )
    unique_scope = fields.Selection(
        selection=[
            ("global", "Across companies"),
            ("company", "Within a company"),
            ("none", "Not unique"),
        ],
        default="global",
        required=True,
    )
    kind_ids = fields.Many2many(
        comodel_name="resource.asset.kind",
        relation="resource_asset_kind_identifier_type_rel",
        column1="type_id",
        column2="kind_id",
        string="Required For",
    )

    _code_uniq = models.Constraint(
        "UNIQUE(code)", "Each identifier type code must be unique."
    )

    @api.constrains("pattern")
    def _check_pattern(self):
        for record in self.filtered("pattern"):
            try:
                re.compile(record.pattern)
            except re.error as error:
                raise ValidationError(
                    self.env._(
                        "%(name)s: invalid pattern (%(error)s).",
                        name=record.name,
                        error=error,
                    )
                ) from error

    @api.model
    def _normalize(self, value):
        return re.sub(r"[^0-9A-Z]", "", (value or "").upper())
