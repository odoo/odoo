import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResourceAssetIdentifier(models.Model):
    _name = "resource.asset.identifier"
    _description = "Asset Identifier"
    _order = "type_id, id"
    _rec_name = "value"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="asset_id.company_id",
    )
    type_id = fields.Many2one(
        comodel_name="resource.asset.identifier.type",
        index=True,
        required=True,
        ondelete="restrict",
    )
    value = fields.Char(required=True)
    normalized_value = fields.Char(
        compute="_compute_normalized_value",
        store=True,
        index="btree_not_null",
    )
    valid_until = fields.Date()

    _type_value_idx = models.Index("(type_id, normalized_value)")
    _asset_type_uniq = models.Constraint(
        "UNIQUE(asset_id, type_id)", "An asset carries one value per identifier type."
    )

    @api.constrains("value", "type_id")
    def _check_pattern(self):
        for identifier in self:
            pattern = identifier.type_id.pattern
            if pattern and not re.fullmatch(pattern, identifier.normalized_value or ""):
                _debug.logic(
                    "identifier.refused", reason="pattern", identifier=identifier
                )
                raise ValidationError(
                    self.env._(
                        "%(value)s is not a valid %(type)s.",
                        value=identifier.value,
                        type=identifier.type_id.name,
                    )
                )

    @api.constrains("normalized_value", "type_id", "asset_id", "company_id")
    def _check_unique(self):
        candidates = self.filtered(
            lambda i: i.normalized_value and i.type_id.unique_scope != "none"
        )
        if not candidates:
            return
        others = self.sudo().search(
            Domain("id", "not in", candidates.ids)
            & Domain("type_id", "in", candidates.type_id.ids)
            & Domain("normalized_value", "in", candidates.mapped("normalized_value"))
        )
        taken = defaultdict(self.env["resource.asset.identifier"].sudo)
        for other in others:
            taken[(other.type_id.id, other.normalized_value)] |= other
        for identifier in candidates:
            holders = taken[(identifier.type_id.id, identifier.normalized_value)]
            if identifier.type_id.unique_scope == "company":
                holders = holders.filtered(
                    lambda h, c=identifier.company_id: h.company_id == c
                )
            holders = holders.filtered(lambda h, a=identifier.asset_id: h.asset_id != a)
            if holders:
                _debug.logic(
                    "identifier.refused", reason="duplicate", identifier=identifier
                )
                raise ValidationError(
                    self.env._(
                        "%(type)s %(value)s already identifies %(asset)s.",
                        type=identifier.type_id.name,
                        value=identifier.value,
                        asset=holders[0].asset_id.display_name,
                    )
                )

    @api.depends("value")
    def _compute_normalized_value(self):
        normalize = self.env["resource.asset.identifier.type"]._normalize
        for identifier in self:
            identifier.normalized_value = normalize(identifier.value)

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if not operator.endswith("like") or not isinstance(value, str):
            return domain
        normalized = self.env["resource.asset.identifier.type"]._normalize(value)
        if not normalized:
            return domain
        by_normalized = Domain("normalized_value", operator, normalized)
        if operator in Domain.NEGATIVE_OPERATORS:
            return Domain(domain) & by_normalized
        return Domain(domain) | by_normalized

    @api.depends("type_id.name", "value")
    def _compute_display_name(self):
        for identifier in self:
            identifier.display_name = f"{identifier.type_id.name}: {identifier.value}"
