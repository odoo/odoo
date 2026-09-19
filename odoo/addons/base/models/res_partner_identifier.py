from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResPartnerIdentifier(models.Model):
    _name = "res.partner.identifier"
    _description = "Partner Identifier"
    _order = "type_id, id"
    _rec_name = "value"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        required=True,
        ondelete="cascade",
    )
    type_id = fields.Many2one(
        comodel_name="res.partner.identifier.type",
        index=True,
        required=True,
        ondelete="restrict",
    )
    value = fields.Char(
        required=True,
        help="As it is written on the document. Comparison ignores case and "
        "punctuation.",
    )
    normalized_value = fields.Char(
        compute="_compute_normalized_value",
        store=True,
        index=True,
        help="Punctuation and case removed, so two spellings of one identifier "
        "compare and deduplicate as one.",
    )
    valid_until = fields.Date(
        index="btree_not_null",
        help="Date the document carrying this identifier expires. Leave empty "
        "for an identifier that does not expire.",
    )
    document_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Documents",
        domain=[("res_model", "=", "res.partner.identifier")],
    )
    company_id = fields.Many2one(
        related="partner_id.company_id",
    )

    _type_value_index = models.Index("(type_id, normalized_value)")

    @api.depends("value")
    def _compute_normalized_value(self):
        normalize = self.env["res.partner.identifier.type"]._normalize
        for identifier in self:
            identifier.normalized_value = normalize(identifier.value)

    @api.depends("type_id", "value")
    def _compute_display_name(self):
        for identifier in self:
            identifier.display_name = f"{identifier.type_id.name}: {identifier.value}"

    @api.constrains("type_id", "value")
    def _check_value_is_valid(self):
        _debug.logic("identifier_values_checked", count=len(self))
        for identifier in self:
            identifier.type_id.check_value(identifier.value)

    @api.constrains("partner_id", "type_id")
    def _check_one_per_contact(self):
        candidates = self.filtered(lambda i: not i.type_id.multiple_per_contact)
        if not candidates:
            _debug.logic("one_per_contact_skipped", count=len(self))
            return
        held = defaultdict(list)
        for other in self.search(
            [
                ("partner_id", "in", candidates.partner_id.ids),
                ("type_id", "in", candidates.type_id.ids),
            ]
        ):
            held[(other.partner_id.id, other.type_id.id)].append(other.id)
        _debug.logic(
            "one_per_contact_check", candidates=len(candidates), held_keys=len(held)
        )
        for identifier in candidates:
            key = (identifier.partner_id.id, identifier.type_id.id)
            if len(held.get(key, ())) > 1:
                _debug.logic(
                    "one_per_contact_violated",
                    partner=identifier.partner_id.id,
                    type=identifier.type_id.id,
                    held=len(held[key]),
                )
                raise ValidationError(
                    self.env._(
                        "%(partner)s already has a %(type)s.",
                        partner=identifier.partner_id.display_name,
                        type=identifier.type_id.display_name,
                    )
                )

    @api.constrains("type_id", "normalized_value", "partner_id")
    def _check_not_taken_by_another_contact(self):
        candidates = self.filtered(lambda i: i.type_id.unique_across_contacts)
        if not candidates:
            return
        identifier_sudo = self.sudo()
        holders = defaultdict(identifier_sudo.browse)
        for other in identifier_sudo.search(
            [
                ("type_id", "in", candidates.type_id.ids),
                ("normalized_value", "in", candidates.mapped("normalized_value")),
            ]
        ):
            holders[(other.type_id.id, other.normalized_value)] |= other
        _debug.logic(
            "identifier_uniqueness",
            candidates=len(candidates),
            holders=sum(len(v) for v in holders.values()),
        )
        for identifier in candidates:
            commercial = identifier.partner_id.commercial_partner_id
            taken = holders[
                (identifier.type_id.id, identifier.normalized_value)
            ].filtered(
                lambda other, commercial=commercial, identifier=identifier: (
                    other != identifier
                    and other.partner_id.commercial_partner_id != commercial
                )
            )
            if taken:
                _debug.logic(
                    "identifier_taken",
                    identifier=identifier.id,
                    type=identifier.type_id.id,
                    holder=taken[0].partner_id.id,
                )
                raise ValidationError(
                    self.env._(
                        "%(value)s is already the %(type)s of %(other)s.",
                        value=identifier.value,
                        type=identifier.type_id.display_name,
                        other=taken[0].partner_id.display_name,
                    )
                )
