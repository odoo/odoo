from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SolarDocumentType(models.Model):
    _name = "solar.document.type"
    _description = "Solar Document Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Document type code must be unique."),
    ]

    @api.constrains("code")
    def _check_code_unique(self):
        for rec in self:
            if self.search_count([("code", "=", rec.code), ("id", "!=", rec.id)]) > 0:
                raise ValidationError(
                    f'Document type code "{rec.code}" already exists.',
                )
