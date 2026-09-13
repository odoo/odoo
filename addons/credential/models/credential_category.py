from odoo import api, fields, models


class CredentialCategory(models.Model):
    _name = "credential.category"
    _description = "Credential Category"
    _order = "sequence, name"

    name = fields.Char(
        string="Category Name",
        translate=True,
        required=True,
        help="Display name for this credential category",
    )
    code = fields.Char(
        string="Technical Code",
        index=True,
        required=True,
        help="Technical identifier (e.g., 'api_key', 'oauth2'). Used for programmatic access.",
    )
    description = fields.Text(
        translate=True,
        help="Detailed description of this credential type",
    )
    sequence = fields.Integer(
        default=10,
        help="Display order in lists",
    )
    active = fields.Boolean(
        default=True,
        help="Inactive categories cannot be used for new credentials",
    )
    storage_hint = fields.Selection(
        selection=[
            ("simple", "Simple Value"),
            ("json", "JSON Data"),
        ],
        string="Storage Type",
        default="simple",
        required=True,
        help="Recommended storage method for credentials of this type:\n"
        "• Simple Value: Single string (API keys, tokens)\n"
        "• JSON Data: Multiple key-value pairs (OAuth2, Basic Auth)",
    )
    icon = fields.Char(
        default="fa-key",
        help="FontAwesome icon class for UI display",
    )

    default_decrypt_rate_limit_enabled = fields.Boolean(
        string="Enable Rate Limiting (Default)",
        default=True,
        help="Default rate limiting setting for credentials of this category. Can be overridden per credential.",
    )
    default_decrypt_rate_limit_max = fields.Integer(
        string="Rate Limit (Default)",
        default=100,
        help="Default maximum decryption attempts per hour. Can be overridden per credential.",
    )
    default_auto_validate_health = fields.Boolean(
        string="Auto Health Check (Default)",
        default=False,
        help="Default setting for automatic health validation. Can be overridden per credential.",
    )
    default_allow_key_fallback = fields.Boolean(
        string="Allow Key Fallback (Default)",
        default=True,
        help="Default setting for allowing decryption with old key versions. Can be overridden per credential.",
    )

    requirement_message = fields.Char(
        translate=True,
        help="Sentence shown when a credential of this category is saved without "
        "one of the values it requires. Generated from the field labels when "
        "left empty.",
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
