import re
from typing import Self

from odoo import Command, api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

PHONE_NOISE_PATTERN = re.compile(r"[\s\\./\(\)\-]")

PHONE_TYPES = [
    ("mobile", "Mobile"),
    ("landline", "Landline"),
    ("fax", "Fax"),
    ("whatsapp", "WhatsApp"),
    ("emergency", "Emergency"),
]


class PhoneNumber(models.Model):
    _name = "phone.number"
    _description = "Phone Number"
    _order = "primary desc, sequence, id"
    _rec_name = "number"
    _rec_names_search = ["number", "sanitized", "label"]
    _name_create_on_import = True

    number = fields.Char(required=True)
    sanitized = fields.Char(
        compute="_compute_sanitized",
        store=True,
        index=True,
        readonly=True,
    )
    type = fields.Selection(
        selection=PHONE_TYPES,
        default="mobile",
        required=True,
    )
    country_id = fields.Many2one(comodel_name="res.country")
    primary = fields.Boolean(default=False)
    sequence = fields.Integer(default=10)
    label = fields.Char()
    note = fields.Text()
    active = fields.Boolean(default=True)
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="res_partner_phone_number_rel",
        column1="phone_number_id",
        column2="partner_id",
        string="Contacts",
    )

    _unique_sanitized = models.Constraint(
        "unique(sanitized)",
        "This phone number already exists.",
    )

    @api.model
    def _normalize_number(self, number: str, country=None) -> str:
        number = PHONE_NOISE_PATTERN.sub("", number or "")
        if number.startswith("00"):
            _debug.logic("sanitize_prefix_rewritten", country=bool(country))
            number = "+" + number[2:]
        return number

    def _get_phone_country(self):
        return self.country_id or self.partner_ids[:1].country_id

    @api.depends("number", "country_id", "partner_ids.country_id")
    def _compute_sanitized(self) -> None:
        _debug.perf.count("sanitized_computed", phones=len(self))
        for phone in self:
            phone.sanitized = self._normalize_number(
                phone.number, phone._get_phone_country()
            )

    @api.depends("number", "label", "type")
    def _compute_display_name(self) -> None:
        for phone in self:
            phone.display_name = (
                f"{phone.number} ({phone.label})" if phone.label else phone.number
            )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        wanted = [
            self._normalize_number(
                vals.get("number"), self._get_country_from_vals(vals)
            )
            for vals in vals_list
        ]
        existing = {
            phone.sanitized: phone
            for phone in self.with_context(active_test=False).search(
                [("sanitized", "in", [s for s in wanted if s])]
            )
        }
        to_create, by_position = [], {}
        first_position, deferred = {}, []
        for position, (vals, sanitized) in enumerate(
            zip(vals_list, wanted, strict=True)
        ):
            if phone := existing.get(sanitized):
                _debug.logic("create_reused", position=position, phone=phone.id)
                phone._link_existing(vals)
                by_position[position] = phone
            elif sanitized and sanitized in first_position:
                _debug.logic(
                    "create_deduplicated",
                    position=position,
                    first=first_position[sanitized],
                )
                deferred.append((position, first_position[sanitized], vals))
            else:
                to_create.append((position, vals))
                first_position[sanitized] = position
        created = super().create([vals for _, vals in to_create])
        _debug.lifecycle(
            "create",
            requested=len(vals_list),
            reused=len(existing),
            deduplicated=len(deferred),
            created=len(created),
        )
        for (position, _), phone in zip(to_create, created, strict=True):
            by_position[position] = phone
        for position, first, vals in deferred:
            phone = by_position[first]
            phone._link_existing(vals)
            by_position[position] = phone
        return self.browse(by_position[i].id for i in range(len(vals_list)))

    @api.model
    def _get_country_from_vals(self, vals: ValuesType):
        if vals.get("country_id"):
            _debug.logic("country_from_vals", by="country_id")
            return self.env["res.country"].browse(vals["country_id"])
        partner_ids = [
            id_
            for command in (vals.get("partner_ids") or [])
            if isinstance(command, (list, tuple))
            for id_ in (
                command[2]
                if command[0] == Command.SET
                else [command[1]]
                if command[0] == Command.LINK
                else []
            )
        ]
        _debug.logic("country_from_vals", by="partner", partners=len(partner_ids))
        return self.env["res.partner"].browse(partner_ids[:1]).country_id

    def _link_existing(self, vals: ValuesType) -> None:
        relational = {
            fname: [
                Command.link(id_)
                for command in value
                if command[0] == Command.SET
                for id_ in command[2]
            ]
            + [command for command in value if command[0] != Command.SET]
            for fname, value in vals.items()
            if self._fields[fname].type == "many2many" and isinstance(value, list)
        }
        if not self.active:
            relational["active"] = True
        _debug.logic(
            "link_existing",
            phone=self.id,
            reactivated=not self.active,
            fields=list(relational),
        )
        if relational:
            self.write(relational)

    def _primary(self, *types: str) -> Self:
        candidates = (
            self.filtered(lambda p: p.type in types) if types else self
        ) or self
        _debug.logic(
            "primary_resolved",
            phones=len(self),
            types=list(types),
            fallback=bool(types) and candidates is self,
        )
        return candidates[:1]
