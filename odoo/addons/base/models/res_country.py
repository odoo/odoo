import logging
import re
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.api import DomainType, ValuesType
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import frozendict
from odoo.tools.translate import _

from odoo.addons.base.models.mixin_catalog import name_uniq_index

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


FLAG_MAPPING = {
    "GF": "fr",
    "BV": "no",
    "BQ": "nl",
    "GP": "fr",
    "HM": "au",
    "YT": "fr",
    "RE": "fr",
    "MF": "fr",
    "UM": "us",
    "XI": "uk",
}

NO_FLAG_COUNTRIES = [
    "AQ",
    "SJ",
]


def _normalize_code(vals: dict[str, Any]) -> dict[str, Any]:
    if code := vals.get("code"):
        return {**vals, "code": code.upper()}
    return vals


class ResCountry(models.Model):
    _name = "res.country"
    _description = "Country"
    _order = "name, id"
    _rec_names_search = ["name", "code"]

    name = fields.Char(
        string="Country Name",
        translate=True,
        required=True,
    )
    code = fields.Char(
        string="Country Code",
        size=2,
        required=True,
        help="The ISO country code in two chars. \nYou can use this field for quick search.",
    )
    address_format = fields.Text(
        string="Layout in Reports",
        default="%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s",
        help="Display format to use for addresses belonging to this country.\n\n"
        "You can use python-style string pattern with all the fields of the address "
        "(for example, use '%(street)s' to display the field 'street') plus"
        "\n%(state_name)s: the name of the state"
        "\n%(state_code)s: the code of the state"
        "\n%(country_name)s: the name of the country"
        "\n%(country_code)s: the code of the country",
    )
    address_view_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Input View",
        domain=[("model", "=", "res.partner"), ("type", "=", "form")],
        help="Use this field if you want to replace the usual way to encode a complete address. "
        "Note that the address_format field is used to modify the way to display addresses "
        "(in reports for example), while this field is used to modify the input form for "
        "addresses.",
    )
    currency_id = fields.Many2one(comodel_name="res.currency")
    image_url = fields.Char(
        string="Flag",
        compute="_compute_image_url",
        help="Url of static flag image",
    )
    phone_code = fields.Integer(string="Country Calling Code")
    country_group_ids = fields.Many2many(
        comodel_name="res.country.group",
        relation="res_country_res_country_group_rel",
        column1="res_country_id",
        column2="res_country_group_id",
        string="Country Groups",
    )
    country_group_codes = fields.Json(compute="_compute_country_group_codes")
    state_ids = fields.One2many(
        comodel_name="res.country.state",
        inverse_name="country_id",
        string="States",
    )
    name_position = fields.Selection(
        selection=[
            ("before", "Before Address"),
            ("after", "After Address"),
        ],
        string="Customer Name Position",
        default="before",
        help="Determines where the customer/company name should be placed, i.e. after or before the address.",
    )
    vat_label = fields.Char(
        translate=True,
        prefetch=True,
        help="Use this field if you want to change vat label.",
    )

    state_required = fields.Boolean(default=False)
    zip_required = fields.Boolean(default=True)

    _name_src_uniq = name_uniq_index(
        message="The name of the country must be unique!",
    )
    _code_uniq = models.Constraint(
        "unique (code)",
        "The code of the country must be unique!",
    )

    @api.model
    def name_search(
        self,
        name: str = "",
        domain: DomainType | None = None,
        operator: str = "ilike",
        limit: int = 100,
    ) -> list[tuple[int, str]]:
        result = []
        domain = Domain(domain or Domain.TRUE)
        if operator not in Domain.NEGATIVE_OPERATORS and name and len(name) == 2:
            countries = self.search_fetch(
                domain & Domain("code", operator, name),
                ["display_name"],
                limit=limit,
            )
            result.extend((country.id, country.display_name) for country in countries)
            _debug.logic("country_name_search", by="code", matched=len(countries))
            domain &= Domain("id", "not in", countries.ids)
            if limit is not None:
                limit -= len(countries)
                if limit <= 0:
                    return result
        result.extend(super().name_search(name, domain, operator, limit))
        return result

    @api.model
    @tools.ormcache("code", cache="stable")
    def _get_phone_code_by_code(self, code: str) -> int:
        phone_code = self.search([("code", "=", code)]).phone_code
        _debug.perf.count("phone_code_computed", code=code, phone_code=phone_code)
        return phone_code

    @api.model
    @tools.ormcache(cache="stable")
    def _get_id_by_code(self) -> frozendict[str, int]:
        by_code = frozendict(
            (country.code, country.id)
            for country in self.sudo().search_fetch([], ["code"])
            if country.code
        )
        _debug.perf.count("country_ids_by_code_computed", countries=len(by_code))
        return by_code

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        self.env.registry.clear_cache("stable")
        vals_list = [_normalize_code(vals) for vals in vals_list]
        _debug.lifecycle("create", codes=[vals.get("code") for vals in vals_list])
        return super().create(vals_list)

    def write(self, vals: dict[str, Any]) -> bool:
        vals = _normalize_code(vals)
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        res = super().write(vals)
        if "code" in vals or "phone_code" in vals:
            _debug.lifecycle("stable_cache_cleared", by="write", count=len(self))
            self.env.registry.clear_cache("stable")
        return res

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", codes=self.mapped("code"))
        self.env.registry.clear_cache("stable")
        return super().unlink()

    def get_fields_address(self) -> list[str]:
        self.check_singleton()
        return re.findall(r"%\((\w+)\)s", self.address_format or "")

    @api.depends("code")
    def _compute_image_url(self) -> None:
        flagless = 0  # debuglog
        for country in self:
            if not country.code or country.code in NO_FLAG_COUNTRIES:
                country.image_url = False
                flagless += 1  # debuglog
            else:
                code = FLAG_MAPPING.get(country.code, country.code.lower())
                country.image_url = f"/base/static/img/country_flags/{code}.png"
        _debug.perf.count("image_urls_computed", countries=len(self), flagless=flagless)

    @api.constrains("address_format")
    def _check_address_format(self) -> None:
        address_fields = self.env["res.partner"]._formatting_address_fields() + [
            "state_code",
            "state_name",
            "country_code",
            "country_name",
            "company_name",
        ]
        test_values = dict.fromkeys(address_fields, "test")
        _debug.logic(
            "address_format_checked", countries=len(self), keys=len(address_fields)
        )
        for record in self:
            if record.address_format:
                try:
                    record.address_format % test_values
                except ValueError, KeyError, TypeError:
                    _debug.logic("address_format_rejected", country=record.code)
                    raise UserError(
                        _("The layout contains an invalid format key")
                    ) from None

    @api.depends("country_group_ids")
    def _compute_country_group_codes(self) -> None:
        for country in self:
            country.country_group_codes = [
                g.code for g in country.country_group_ids if g.code
            ] or [""]


class ResCountryGroup(models.Model):
    _name = "res.country.group"
    _description = "Country Group"

    name = fields.Char(
        translate=True,
        required=True,
    )
    code = fields.Char()
    country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="res_country_res_country_group_rel",
        column1="res_country_group_id",
        column2="res_country_id",
        string="Countries",
    )

    _check_code_uniq = models.Constraint(
        "unique(code)",
        "The country group code must be unique!",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        _debug.lifecycle(
            "country_group_create", codes=[vals.get("code") for vals in vals_list]
        )
        return super().create([_normalize_code(vals) for vals in vals_list])

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("country_group_write", count=len(self), fields=list(vals))
        return super().write(_normalize_code(vals))


class ResCountryState(models.Model):
    _name = "res.country.state"
    _description = "Country state"
    _order = "code, id"
    _rec_names_search = ["name", "code"]

    country_id = fields.Many2one(
        comodel_name="res.country",
        index=True,
        required=True,
    )
    name = fields.Char(
        string="State Name",
        required=True,
        help="Administrative divisions of a country. E.g. Fed. State, Department, Canton",
    )
    code = fields.Char(
        string="State Code",
        required=True,
        help="The state code.",
    )

    _name_code_uniq = models.Constraint(
        "unique(country_id, code)",
        "The code of the state must be unique by country!",
    )

    @api.model
    def name_search(
        self,
        name: str = "",
        domain: DomainType | None = None,
        operator: str = "ilike",
        limit: int = 100,
    ) -> list[tuple[int, str]]:
        result = []
        domain = Domain(domain or Domain.TRUE)
        if operator == "in":
            if limit is None:
                limit = 100
            _debug.logic("state_name_search", by="terms", terms=len(name), limit=limit)
            for item in name:
                result.extend(
                    self.name_search(  # noqa: E8507  one match per term by design
                        item, domain, operator="=", limit=limit - len(result)
                    )
                )
                if len(result) == limit:
                    break
            return result
        if operator not in Domain.NEGATIVE_OPERATORS and name:
            states = self.search_fetch(
                domain & Domain("code", "=ilike", name),
                ["display_name"],
                limit=limit,
            )
            result.extend((state.id, state.display_name) for state in states)
            _debug.logic("state_name_search", by="code", matched=len(states))
            domain &= Domain("id", "not in", states.ids)
            if limit is not None:
                limit -= len(states)
                if limit <= 0:
                    return result
        result.extend(super().name_search(name, domain, operator, limit))
        return result

    @api.model
    def _search_display_name(self, operator: str, value: str) -> Domain:
        domain = super()._search_display_name(operator, value)
        if value and operator not in Domain.NEGATIVE_OPERATORS:
            if operator in ("ilike", "=") and isinstance(value, str):
                domain |= self._get_domain_name_search(value, operator)
            elif operator == "in":
                domain |= Domain.OR(
                    self._get_domain_name_search(name, "=")
                    for name in value
                    if isinstance(name, str)
                )
        if country_id := self.env.context.get("country_id"):
            domain &= Domain("country_id", "=", country_id)
        _debug.logic(
            "state_display_name_search",
            operator=operator,
            country=self.env.context.get("country_id"),
        )
        return domain

    def _get_domain_name_search(self, name: str, operator: str) -> Domain:
        if m := re.fullmatch(r"(?P<name>.+)\((?P<country>.+)\)", name):
            _debug.logic(
                "state_name_with_country_parsed",
                operator=operator,
                country=m["country"].strip(),
            )
            return Domain(
                [
                    ("name", operator, m["name"].strip()),
                    "|",
                    ("country_id.name", "ilike", m["country"].strip()),
                    ("country_id.code", "=", m["country"].strip()),
                ]
            )
        return Domain.FALSE

    @api.depends("country_id.code")
    @api.depends_context("formatted_display_name")
    def _compute_display_name(self) -> None:
        formatted = self.env.context.get("formatted_display_name")
        for record in self:
            code = record.country_id.code
            if formatted:
                record.display_name = f"{record.name} \t --{code}--"
            else:
                record.display_name = f"{record.name} ({code})"
