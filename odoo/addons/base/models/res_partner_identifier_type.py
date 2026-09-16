import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

from .mixin_catalog import name_uniq_index

_debug = DebugLog(__name__)

_NON_ALPHANUMERIC = re.compile(r"[^\w&]+|_+")


class ResPartnerIdentifierType(models.Model):
    _name = "res.partner.identifier.type"
    _inherit = ["mixin.catalog"]
    _description = "Partner Identifier Type"
    _order = "sequence, name"

    code = fields.Char(
        required=True,
        help="Stable key this type is resolved by. Localizations and "
        "integrations name the code, never the label, which is translated "
        "and editable.",
    )
    sequence = fields.Integer(default=10)
    country_ids = fields.Many2many(
        comodel_name="res.country",
        string="Countries",
        help="Offer this identifier only for contacts in these countries. "
        "Leave empty to offer it everywhere.",
    )
    pattern = fields.Char(
        string="Format",
        help="Optional regular expression the normalized value must match, "
        "anchored at both ends. Checked before any code-specific rule.",
    )
    unique_across_contacts = fields.Boolean(
        default=True,
        help="Refuse a value another contact already carries under this type. "
        "Turn it off for an identifier that is legitimately shared, such as a "
        "group-wide registration.",
    )
    multiple_per_contact = fields.Boolean(
        default=False,
        help="Allow one contact to carry several values of this type.",
    )
    confidential = fields.Boolean(
        default=False,
        help="Restrict this identifier to its own holder and to the groups "
        "granted full access by a record rule. Use it for what identifies a "
        "person to the state -- a national number, a passport -- and leave it "
        "off for what a company publishes about itself, such as a tax ID.",
    )
    synced_with_commercial = fields.Boolean(
        default=False,
        help="Copy this identifier from the commercial entity down to its "
        "contacts. Use it for what identifies the *company* -- a tax ID -- and "
        "leave it off for what identifies a person, such as a national number.",
    )

    _code_uniq = models.Constraint(
        "UNIQUE(code)",
        "An identifier type with this code already exists.",
    )
    _name_src_uniq = name_uniq_index(
        message="An identifier type with this name already exists.",
    )

    @api.constrains("pattern")
    def _check_pattern_compiles(self):
        for identifier_type in self:
            if not identifier_type.pattern:
                continue
            try:
                re.compile(identifier_type.pattern)
            except re.error as error:
                _debug.logic(
                    "pattern_rejected", type=identifier_type.code, error=str(error)
                )
                raise ValidationError(
                    self.env._(
                        "%(name)s: the format is not a valid regular "
                        "expression (%(error)s).",
                        name=identifier_type.display_name,
                        error=error,
                    )
                ) from error

    @api.model
    def _normalize(self, value):
        return _NON_ALPHANUMERIC.sub("", value or "").upper()

    def check_value(self, value):
        self.check_singleton()
        normalized = self._normalize(value)
        if not normalized:
            _debug.logic("identifier_rejected", type=self.code, reason="empty")
            raise ValidationError(
                self.env._("%(name)s cannot be empty.", name=self.display_name)
            )
        if self.pattern and not re.fullmatch(self.pattern, normalized):
            _debug.logic("identifier_rejected", type=self.code, reason="pattern")
            raise ValidationError(
                self.env._(
                    "%(value)s is not a valid %(name)s.",
                    value=value,
                    name=self.display_name,
                )
            )
        checker = getattr(self, f"_check_code_{(self.code or '').lower()}", None)
        _debug.logic(
            "identifier_checked",
            type=self.code,
            pattern=bool(self.pattern),
            checker=checker.__name__ if checker else None,
        )
        if checker and not checker(normalized):
            _debug.logic("identifier_rejected", type=self.code, reason="checker")
            raise ValidationError(
                self.env._(
                    "%(value)s is not a valid %(name)s.",
                    value=value,
                    name=self.display_name,
                )
            )
        self._check_hook(normalized)
        return normalized

    def _check_hook(self, normalized):
        pass

    @api.model
    def _get_type_by_code(self, code):
        identifier_type = self.search([("code", "=", code)], limit=1)
        _debug.perf.count(
            "identifier_type_by_code", code=code, found=bool(identifier_type)
        )
        return identifier_type
