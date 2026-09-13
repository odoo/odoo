import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

STORAGE_FIELD_CODES = frozenset({"credential_value"})


class CredentialCategoryField(models.Model):
    _name = "credential.category.field"
    _description = "Field a Credential Category Holds"
    _order = "category_id, sequence, code"

    category_id = fields.Many2one(
        comodel_name="credential.category",
        index=True,
        required=True,
        ondelete="cascade",
    )
    code = fields.Char(
        required=True,
        help="Key this value is stored under inside the encrypted payload.",
    )
    name = fields.Char(
        required=True,
        help="Label shown on the credential form.",
    )
    sequence = fields.Integer(default=10)
    placeholder = fields.Char()
    help_text = fields.Char()
    required = fields.Boolean(
        default=True,
        help="A credential of this category cannot be saved without a value.",
    )
    requirement_group = fields.Char(
        help="Fields sharing a group satisfy the requirement between them, so any "
        "one of them is enough. Leave empty to require this field on its own."
    )
    is_blob_key = fields.Boolean(
        compute="_compute_is_blob_key",
        store=True,
        help="Stored inside the encrypted JSON payload rather than as the whole "
        "payload of the simple storage mode.",
    )

    _code_uniq = models.Constraint(
        "UNIQUE(category_id, code)",
        "A category names each of its fields once.",
    )

    @api.depends("code")
    def _compute_is_blob_key(self):
        for definition in self:
            definition.is_blob_key = definition.code not in STORAGE_FIELD_CODES

    @api.constrains("code")
    def _check_code_is_a_payload_key(self):
        for definition in self:
            if not CODE_RE.match(definition.code or ""):
                raise ValidationError(
                    self.env._(
                        "'%(code)s' cannot be a key in the encrypted payload. Use "
                        "lowercase letters, digits and underscores, starting with "
                        "a letter.",
                        code=definition.code,
                    )
                )

    def _requirement_specs(self):
        specs = []
        by_group = {}
        for definition in self.filtered("required"):
            group = definition.requirement_group
            if not group:
                specs.append(definition)
            elif group in by_group:
                by_group[group] |= definition
            else:
                by_group[group] = definition
                specs.append(group)
        return [by_group[spec] if isinstance(spec, str) else spec for spec in specs]
