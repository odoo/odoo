from odoo import api, fields, models


class CredentialCategory(models.Model):
    _name = "credential.category"
    _description = "Credential Category"
    _order = "sequence, name"

    name = fields.Char(
        string="Category Name",
        help="Display name for this credential category",
        translate=True,
        required=True,
    )
    code = fields.Char(
        string="Technical Code",
        help="Technical identifier (e.g., 'api_key', 'oauth2'). Used for programmatic access.",
        index=True,
        required=True,
    )
    description = fields.Text(
        help="Detailed description of this credential type",
        translate=True,
    )
    sequence = fields.Integer(
        help="Display order in lists",
        default=10,
    )
    active = fields.Boolean(
        help="Inactive categories cannot be used for new credentials",
        default=True,
    )
    storage_hint = fields.Selection(
        selection=[
            ("simple", "Simple Value"),
            ("json", "JSON Data"),
        ],
        string="Storage Type",
        help="Recommended storage method for credentials of this type:\n"
        "• Simple Value: Single string (API keys, tokens)\n"
        "• JSON Data: Multiple key-value pairs (OAuth2, Basic Auth)",
        default="simple",
        required=True,
    )
    icon = fields.Char(
        help="FontAwesome icon class for UI display",
        default="fa-key",
    )

    default_decrypt_rate_limit_enabled = fields.Boolean(
        string="Enable Rate Limiting (Default)",
        help="Default rate limiting setting for credentials of this category. Can be overridden per credential.",
        default=True,
    )
    default_decrypt_rate_limit_max = fields.Integer(
        string="Rate Limit (Default)",
        help="Default maximum decryption attempts per hour. Can be overridden per credential.",
        default=100,
    )
    default_auto_validate_health = fields.Boolean(
        string="Auto Health Check (Default)",
        help="Default setting for automatic health validation. Can be overridden per credential.",
        default=False,
    )
    default_allow_key_fallback = fields.Boolean(
        string="Allow Key Fallback (Default)",
        help="Default setting for allowing decryption with old key versions. Can be overridden per credential.",
        default=True,
    )

    requirement_message = fields.Char(
        help="Sentence shown when a credential of this category is saved without "
        "one of the values it requires. Generated from the field labels when "
        "left empty.",
        translate=True,
    )

    field_ids = fields.One2many(
        comodel_name="credential.category.field",
        inverse_name="category_id",
        string="Fields",
        help="Values a credential of this category holds, each one a key in the "
        "encrypted payload.",
    )

    credential_ids = fields.One2many(
        comodel_name="credential.credential",
        inverse_name="category_id",
        string="Credentials",
        help="Credentials of this category",
    )
    credential_count = fields.Integer(
        compute="_compute_credential_count",
        store=False,
    )

    _code_uniq = models.Constraint(
        "unique(code)",
        "Category code must be unique!",
    )

    def _requirement_message(self) -> str:
        self.check_singleton()
        if self.requirement_message:
            return self.requirement_message
        alternatives = [
            " or ".join(dict.fromkeys(definition.name for definition in spec))
            for spec in self.field_ids._requirement_specs()
        ]
        return self.env._(
            "%(category)s credentials require %(fields)s.",
            category=self.name,
            fields=", ".join(alternatives),
        )

    @api.depends("name", "code")
    def _compute_display_name(self):
        for category in self:
            category.display_name = f"{category.name} ({category.code})"

    @api.depends("credential_ids")
    def _compute_credential_count(self):
        counts = dict(
            self.env["credential.credential"]._read_group(
                [("category_id", "in", self.ids)],
                groupby=["category_id"],
                aggregates=["__count"],
            )
        )
        for category in self:
            category.credential_count = counts.get(category, 0)
