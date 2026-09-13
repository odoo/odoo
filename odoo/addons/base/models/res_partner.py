import base64
import datetime
import logging
import re
import typing
from collections import defaultdict
from typing import Any, Literal, Self
from urllib.parse import urlsplit, urlunsplit

from odoo import Command, _, api, fields, models, tools
from odoo.api import ValuesType
from odoo.db import FunctionStatus
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.libs.datetime import all_timezones
from odoo.libs.datetime import timezone as get_timezone
from odoo.libs.debug_log import DebugLog
from odoo.libs.text import name_length_band, similarity_ratio
from odoo.tools import SQL

if typing.TYPE_CHECKING:
    from .res_partner_tag import ResPartnerTag
    from .res_users import ResUsers

from .mixin_format_address import ADDRESS_FIELDS

POSITION_FIELDS = ("partner_latitude", "partner_longitude")

SIMILAR_NAME_THRESHOLD_PARAM = "base.partner_name_similarity_threshold"
DEFAULT_SIMILAR_NAME_THRESHOLD = 0.75

SIMILAR_NAME_RECALL_LIMIT = 200

EU_EXTRA_VAT_CODES = {
    "GR": "EL",
    "GB": "XI",
}

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_FAILED_ADDRESS_FORMATS: set[tuple[str, str]] = set()


def _is_distinct_partner(
    candidate: Any,
    partner_id: int | bool,
    country_id: int | None,
    company_id: int | None,
    company_scoped: bool = False,
) -> bool:
    if candidate.id == partner_id:
        return False
    if partner_id and _is_descendant_of(candidate, partner_id):
        return False
    if country_id and candidate.country_id.id and candidate.country_id.id != country_id:
        return False
    return not (
        candidate.company_id.id
        and candidate.company_id.id != company_id
        and (company_scoped or company_id)
    )


def _get_duplicate(
    partner_id: int | bool,
    values: list[str],
    candidates_by_value: dict[str, list],
    country_id: int | None,
    company_id: int | None,
    company_scoped: bool = False,
) -> ResPartner | Literal[False]:
    for value in values:
        for candidate in candidates_by_value.get(value, []):
            if _is_distinct_partner(
                candidate, partner_id, country_id, company_id, company_scoped
            ):
                return candidate
    return False


def _is_descendant_of(candidate: Any, ancestor_id: int) -> bool:
    seen = set()
    record = candidate
    while record := record.parent_id:
        if record.id == ancestor_id:
            return True
        if record.id in seen:
            return False
        seen.add(record.id)
    return False


def _selection_installed_langs(self) -> list[tuple[str, str]]:
    return self.env["res.lang"].get_installed()


_tzs = [
    (tz, tz)
    for tz in sorted(all_timezones(), key=lambda tz: (tz.startswith("Etc/"), tz))
]


def _selection_timezones(self) -> list[tuple[str, str]]:
    return _tzs


_RE_WHITESPACE_BEFORE_NEWLINE = re.compile(r"\s+\n")


def _complete_name_trgm_index_definition(registry) -> str:
    if not registry.has_trigram:
        return ""

    expression = '"complete_name"'
    if registry.has_unaccent == FunctionStatus.INDEXABLE:
        expression = registry.unaccent(expression)
    return f"USING gin ({expression} gin_trgm_ops)"


class ResPartner(models.Model):
    _name = "res.partner"
    _description = "Contact"
    _inherit = [
        "mixin.format.address",
        "mixin.format.vat.label",
        "mixin.avatar",
        "mixin.properties.base.definition",
    ]
    _order = "complete_name ASC, id DESC"
    _rec_names_search = [
        "complete_name",
        "email",
        "ref",
        "vat",
        "company_registry",
    ]
    _allow_sudo_commands = False
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    _complete_name_displayed_types = ("invoice", "delivery", "other", "private")
    _display_name_column = "complete_name"
    _display_name_column_guard = "name"
    _display_name_context_keys = (
        "formatted_display_name",
        "show_email",
        "partner_show_db_id",
        "show_address",
        "show_vat",
        "partner_display_name_hide_company",
    )

    company_id = fields.Many2one(
        "res.company",
        "Company",
        index=True,
    )
    name = fields.Char(
        index=True,
        default_export_compatible=True,
    )
    complete_name = fields.Char(
        compute="_compute_complete_name",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)
    color = fields.Integer(
        string="Color Index",
        default=0,
    )

    commercial_partner_id = fields.Many2one(
        "res.partner",
        string="Commercial Entity",
        compute="_compute_commercial_partner_id",
        store=True,
        recursive=True,
        index=True,
    )
    commercial_company_name = fields.Char(
        "Company Name Entity",
        compute="_compute_commercial_company_name",
        store=True,
    )

    parent_id = fields.Many2one(
        "res.partner",
        string="Related Company",
        index=True,
    )
    parent_name = fields.Char(
        related="parent_id.name",
        readonly=True,
        string="Parent name",
    )
    child_ids = fields.One2many(
        "res.partner",
        "parent_id",
        string="Contact",
        domain=[("active", "=", True)],
    )
    user_id: ResUsers = fields.Many2one(
        "res.users",
        string="Salesperson",
        compute="_compute_user_id",
        precompute=True,
        readonly=False,
        store=True,
        help="The internal user in charge of this contact.",
    )
    tag_ids = fields.Many2many(
        "res.partner.tag",
        column1="partner_id",
        column2="tag_id",
        string="Tags",
        default=lambda self: self._default_tag_ids(),
    )
    barcode = fields.Char(
        copy=False,
        company_dependent=True,
        help="Use a barcode to identify this contact.",
    )
    ref = fields.Char(
        string="Reference",
        index=True,
    )
    lang = fields.Selection(
        _selection_installed_langs,
        string="Language",
        compute="_compute_lang",
        readonly=False,
        store=True,
        help="All the emails and documents sent to this contact will be translated in this language.",
    )
    active_lang_count = fields.Integer(
        compute="_compute_active_lang_count",
    )
    tz = fields.Selection(
        _tzs,
        string="Timezone",
        default=lambda self: self.env.context.get("tz"),
        help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
        "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
        "Anywhere else, time values are computed according to the time offset of your web client.",
    )
    tz_offset = fields.Char(
        compute="_compute_tz_offset",
        string="Timezone offset",
    )
    vat = fields.Char(
        string="Tax ID",
        index=True,
        help="The Tax Identification Number. Values here will be validated based on the country format. You can use '/' to indicate that the partner is not subject to tax.",
    )
    vat_label = fields.Char(
        string="Tax ID Label",
        compute="_compute_vat_label",
    )
    same_vat_partner_id = fields.Many2one(
        "res.partner",
        string="Partner with same Tax ID",
        compute="_compute_same_identifier_partners",
        store=False,
    )
    company_registry = fields.Char(
        string="Company ID",
        compute="_compute_company_registry",
        store=True,
        readonly=False,
        index="btree_not_null",
        help="The registry number of the company. Use it if it is different from the Tax ID. It must be unique across all partners of a same country",
    )
    company_registry_label = fields.Char(
        string="Company ID Label",
        compute="_compute_company_registry_label",
    )
    company_registry_placeholder = fields.Char(
        compute="_compute_company_registry_placeholder",
    )
    same_company_registry_partner_id = fields.Many2one(
        "res.partner",
        string="Partner with same Company Registry",
        compute="_compute_same_identifier_partners",
        store=False,
    )
    type = fields.Selection(
        [
            ("contact", "Contact"),
            ("invoice", "Invoice"),
            ("delivery", "Delivery"),
            ("other", "Other"),
            ("private", "Private"),
        ],
        string="Address Type",
        default="contact",
    )
    type_address_label = fields.Char(
        "Address Type Description",
        compute="_compute_type_address_label",
    )
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one(
        "res.country.state",
        string="State",
        ondelete="restrict",
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        ondelete="restrict",
    )
    country_code = fields.Char(
        related="country_id.code",
        string="Country Code",
    )
    nationality_id = fields.Many2one(
        "res.country",
        string="Nationality",
        help="The country this person is a national of. Distinct from the "
        "address country, which says where they are: a person may be resident "
        "in one country and a national of another.",
    )
    contact_address = fields.Char(
        compute="_compute_contact_address",
        string="Complete Address",
    )
    partner_latitude = fields.Float(
        string="Geo Latitude",
        digits=(10, 7),
    )
    partner_longitude = fields.Float(
        string="Geo Longitude",
        digits=(10, 7),
    )
    function = fields.Char(string="Job Position")
    website = fields.Char("Website Link")
    email = fields.Char()
    email_formatted = fields.Char(
        "Formatted Email",
        compute="_compute_email_formatted",
        help='Format email address "Name <email@domain>"',
    )
    phone_ids = fields.Many2many(
        "phone.number",
        "res_partner_phone_number_rel",
        "partner_id",
        "phone_number_id",
        string="Phone Numbers",
    )
    main_phone_id = fields.Many2one(
        "phone.number",
        string="Main Phone",
        compute="_compute_main_phone_ids",
        store=True,
        help="The landline this contact is reached on when a single number is "
        "needed. The first active number typed Landline, by the order phone "
        "numbers carry.",
    )
    main_mobile_id = fields.Many2one(
        "phone.number",
        string="Main Mobile",
        compute="_compute_main_phone_ids",
        store=True,
        help="The mobile this contact is reached on when a single number is "
        "needed. The first active number typed Mobile, by the order phone "
        "numbers carry.",
    )
    gender = fields.Selection(
        selection=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
    )
    birthdate = fields.Date()
    comment = fields.Html(string="Notes")
    industry_ids = fields.Many2many(
        "res.partner.industry",
        relation="res_partner_industry_rel",
        column1="partner_id",
        column2="industry_id",
        string="Industries",
        help="Every sector this contact operates in. A grower that also runs a "
        "packing house belongs to two of them at once.",
    )
    primary_industry_id = fields.Many2one(
        "res.partner.industry",
        string="Primary Industry",
        compute="_compute_primary_industry_id",
        store=True,
        readonly=False,
        help="The one sector analytics report this contact under, because a sum "
        "cannot be split across several. Defaults to the first of Industries, and "
        "returns to it whenever Industries changes and the current pick is no "
        "longer among them.",
    )
    user_ids: ResUsers = fields.One2many(
        "res.users",
        "partner_id",
        string="Users",
        bypass_search_access=True,
    )
    main_user_id = fields.Many2one(
        "res.users",
        string="Main User",
        compute="_compute_main_user_id",
        help="There can be several users related to the same partner. "
        "When a single user is needed, this field attempts to find the most appropriate one.",
    )
    duplicate_ids = fields.Many2many(
        "res.partner",
        string="Possible Duplicates",
        compute="_compute_possible_duplicates",
    )
    duplicate_count = fields.Integer(
        compute="_compute_possible_duplicates",
    )
    identifier_ids = fields.One2many(
        comodel_name="res.partner.identifier",
        inverse_name="partner_id",
        string="Identifiers",
    )
    bank_ids = fields.One2many(
        "res.partner.bank",
        "partner_id",
        string="Banks",
    )
    main_bank_id = fields.Many2one(
        "res.partner.bank",
        string="Main Bank Account",
        compute="_compute_main_bank_id",
        store=True,
        help="The account this contact is paid on when a single one is needed. "
        "The first active account, by the order bank accounts carry.",
    )
    is_company = fields.Boolean(
        string="Is a Company",
        default=False,
        help="Check if the contact is a company, otherwise it is a person",
    )
    is_public = fields.Boolean(
        compute="_compute_is_public",
        compute_sudo=True,
    )
    partner_share = fields.Boolean(
        "Share Partner",
        compute="_compute_partner_share",
        store=True,
        help="Either customer (not a user), either shared user. Indicated the current partner is a customer without "
        "access or with a limited access created for sharing data.",
    )

    application_statistics = fields.Json(
        string="Stats",
        compute="_compute_application_statistics",
    )

    _check_name = models.Constraint(
        "CHECK( COALESCE(type, 'contact') != 'contact' OR name IS NOT NULL )",
        "Contacts require a name",
    )
    _complete_name_trgm_index = models.Index(_complete_name_trgm_index_definition)
    _barcode_gin_index = models.Index("USING gin (barcode jsonb_path_ops)")

    def _compute_application_statistics(self) -> None:
        result = self._get_application_statistics()
        for p in self:
            p.application_statistics = result.get(p.id, [])

    def _get_application_statistics(self) -> defaultdict[int, list]:
        return defaultdict(list)

    def _get_street_split(self) -> dict[str, str]:
        self.check_singleton()
        return tools.street_split(self.street or "")

    @api.depends("name", "user_ids.share", "image_1920", "is_company", "type")
    def _compute_avatar_1920(self) -> None:
        super()._compute_avatar_1920()

    @api.depends("name", "user_ids.share", "image_1024", "is_company", "type")
    def _compute_avatar_1024(self) -> None:
        super()._compute_avatar_1024()

    @api.depends("name", "user_ids.share", "image_512", "is_company", "type")
    def _compute_avatar_512(self) -> None:
        super()._compute_avatar_512()

    @api.depends("name", "user_ids.share", "image_256", "is_company", "type")
    def _compute_avatar_256(self) -> None:
        super()._compute_avatar_256()

    @api.depends("name", "user_ids.share", "image_128", "is_company", "type")
    def _compute_avatar_128(self) -> None:
        super()._compute_avatar_128()

    def _default_tag_ids(self) -> ResPartnerTag:
        return self.env["res.partner.tag"].browse(self.env.context.get("tag_id"))

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        values = super().default_get(fields)
        if "company_id" in fields and "parent_id" in fields and values.get("parent_id"):
            parent = self.browse(values.get("parent_id"))
            values["company_id"] = parent.company_id.id
        if "type" in fields and values.get("type"):
            if values["type"] not in self._fields["type"].get_values(self.env):
                values["type"] = self._fields["type"].default(self)
        return values

    def _update_avatar(self, avatar_field: str, image_field: str) -> None:
        partners_with_internal_user = self.filtered(
            lambda partner: (
                partner.user_ids - partner.user_ids.filtered("share")
                or partner.type == "contact"
            )
        )
        super(ResPartner, partners_with_internal_user)._update_avatar(
            avatar_field, image_field
        )
        partners_without_image = (self - partners_with_internal_user).filtered(
            lambda p: not p[image_field]
        )
        for partner in partners_without_image:
            partner[avatar_field] = base64.b64encode(partner._get_avatar_placeholder())

        for partner in self - partners_with_internal_user - partners_without_image:
            partner[avatar_field] = partner[image_field]

    def _get_avatar_placeholder_path(self) -> str:
        if self.is_company:
            return "base/static/img/company_image.png"
        if self.type == "delivery":
            return "base/static/img/truck.png"
        if self.type == "invoice":
            return "base/static/img/bill.png"
        if self.type == "other":
            return "base/static/img/puzzle.png"
        return super()._get_avatar_placeholder_path()

    def _get_complete_name(self, type_description: dict[str, str]) -> str:
        self.check_singleton()

        name = self.name or ""
        if self.parent_id:
            if not name and self.type in self._complete_name_displayed_types:
                name = type_description[self.type]
            if not self.is_company and not self.env.context.get(
                "partner_display_name_hide_company"
            ):
                name = f"{self.commercial_company_name or self.sudo().parent_id.name}, {name}"
        return name.strip()

    @api.depends(
        "is_company",
        "name",
        "parent_id.name",
        "type",
        "commercial_company_name",
    )
    def _compute_complete_name(self) -> None:
        clean_self = self.with_context({})
        type_description = dict(
            self._fields["type"]._description_selection(clean_self.env)
        )
        for partner in clean_self:
            # normalised exactly as _compute_display_name normalises its result,
            # so the stored column is the display name and not only nearly
            partner.complete_name = _RE_WHITESPACE_BEFORE_NEWLINE.sub(
                "\n", partner._get_complete_name(type_description)
            ).strip()

    @api.depends("parent_id")
    def _compute_lang(self) -> None:
        self.filtered(
            lambda partner: not partner.lang or not partner._origin
        )._update_lang_from_parent()

    def _update_lang_from_parent(self) -> None:
        if not self:
            return
        default_lang = self.default_get(["lang"]).get("lang")
        for partner in self:
            if partner.parent_id:
                partner.lang = partner.parent_id.lang or default_lang or self.env.lang
            elif not partner.lang:
                partner.lang = default_lang or self.env.lang

    def _compute_active_lang_count(self) -> None:
        lang_count = len(self.env["res.lang"].get_installed())
        self.active_lang_count = lang_count

    @api.depends("tz")
    def _compute_tz_offset(self) -> None:
        now = datetime.datetime.now
        tz_cache: dict[str | None, str] = {}
        for partner in self:
            tz = partner.tz or "GMT"
            if (offset := tz_cache.get(tz)) is None:
                offset = tz_cache[tz] = now(get_timezone(tz)).strftime("%z")
            partner.tz_offset = offset

    @api.depends("parent_id")
    def _compute_user_id(self) -> None:
        for partner in self.filtered(
            lambda partner: (
                not partner.user_id
                and not partner.is_company
                and partner.parent_id.user_id
            )
        ):
            partner.user_id = partner.parent_id.user_id

    @api.depends_context("uid")
    @api.depends("user_ids.active", "user_ids.share")
    def _compute_main_user_id(self) -> None:
        Users = self.env["res.users"].sudo()
        current_user = self.env.user
        current_partner_id = current_user.partner_id.id
        root_partner_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "base.partner_root"
        )
        root_user = Users.browse(
            self.env["ir.model.data"]._xmlid_to_res_id("base.user_root")
        )

        best_user: dict[int, ResUsers] = {}
        all_users = Users.search_fetch(
            [("partner_id", "in", self.ids), ("active", "=", True)],
            ["partner_id", "share"],
            order="share ASC, id ASC",
        )
        for user in all_users:
            best_user.setdefault(user.partner_id.id, user)

        for partner in self:
            if partner.id == current_partner_id:
                partner.main_user_id = current_user
            elif partner.id in best_user:
                partner.main_user_id = best_user[partner.id]
            elif partner.id == root_partner_id:
                partner.main_user_id = root_user
            else:
                partner.main_user_id = False

    @api.depends(
        "phone_ids",
        "phone_ids.type",
        "phone_ids.primary",
        "phone_ids.sequence",
        "phone_ids.active",
    )
    def _compute_main_phone_ids(self) -> None:
        sources = self.with_context(active_test=False)
        for partner, source in zip(self, sources, strict=True):
            numbers = source.phone_ids.filtered("active").sorted(
                lambda number: (not number.primary, number.sequence)
            )
            partner.main_phone_id = numbers.filtered(
                lambda number: number.type == "landline"
            )[:1]
            partner.main_mobile_id = numbers.filtered(
                lambda number: number.type == "mobile"
            )[:1]

    @api.depends("bank_ids", "bank_ids.sequence", "bank_ids.active")
    def _compute_main_bank_id(self) -> None:
        sources = self.with_context(active_test=False)
        for partner, source in zip(self, sources, strict=True):
            accounts = source.bank_ids.filtered("active")
            partner.main_bank_id = accounts.sorted("sequence")[:1]

    @api.depends("industry_ids")
    def _compute_primary_industry_id(self) -> None:
        for partner in self:
            if partner.primary_industry_id not in partner.industry_ids:
                partner.primary_industry_id = partner.industry_ids[:1]

    @api.depends("user_ids.share", "user_ids.active")
    def _compute_partner_share(self) -> None:
        super_partner = self.env["res.users"].browse(api.SUPERUSER_ID).partner_id
        if super_partner in self:
            super_partner.partner_share = False

        partners = self - super_partner
        if not partners:
            return

        partners.partner_share = True

        internal_partner_ids = {
            partner.id
            for (partner,) in self.env["res.users"]._read_group(
                [("partner_id", "in", partners.ids), ("share", "=", False)],
                groupby=["partner_id"],
            )
        }
        if internal_partner_ids:
            partners.filtered(
                lambda p: p.id in internal_partner_ids
            ).partner_share = False

    @api.depends_context("uid")
    @api.depends(
        "vat",
        "company_id",
        "company_registry",
        "parent_id",
        "country_id.country_group_codes",
        "country_id.code",
    )
    def _compute_same_identifier_partners(self) -> None:
        Partner = self.with_context(active_test=False).sudo()

        all_vats = set()
        all_registries = set()
        vat_variants: dict[int, list[str]] = {}
        for partner in self:
            if partner.vat and partner.vat != "/" and not partner.parent_id:
                vats = [partner.vat]
                if (
                    partner.country_id
                    and "EU_PREFIX" in partner.country_id.country_group_codes
                ):
                    if partner.vat[:2].isalpha():
                        vats.append(partner.vat[2:])
                    else:
                        vats.append(partner.country_id.code + partner.vat)
                        if new_code := EU_EXTRA_VAT_CODES.get(partner.country_id.code):
                            vats.append(new_code + partner.vat)
                vat_variants[partner.id] = vats
                all_vats.update(vats)
            if partner.company_registry and not partner.parent_id:
                all_registries.add(partner.company_registry)

        vat_by_value: dict[str, list] = defaultdict(list)
        if all_vats:
            candidates = Partner.search_fetch(
                [("vat", "in", list(all_vats))],
                ["vat", "parent_id", "company_id", "country_id"],
            )
            for c in candidates.with_env(self.env)._filtered_access("read"):
                vat_by_value[c.vat].append(c)

        reg_by_value: dict[str, list] = defaultdict(list)
        if all_registries:
            candidates = Partner.search_fetch(
                [("company_registry", "in", list(all_registries))],
                ["company_registry", "parent_id", "company_id", "country_id"],
            )
            for c in candidates.with_env(self.env)._filtered_access("read"):
                reg_by_value[c.company_registry].append(c)

        for partner in self:
            partner_id = partner._origin.id
            vats = vat_variants.get(partner.id)

            if vats and any(vat in vat_by_value for vat in vats):
                country_id = partner.country_id.id if partner.country_id else None
                company_id = partner.company_id.id if partner.company_id else None
                partner.same_vat_partner_id = _get_duplicate(
                    partner_id,
                    vats,
                    vat_by_value,
                    country_id,
                    company_id,
                )
            else:
                partner.same_vat_partner_id = False

            if (
                partner.company_registry
                and not partner.parent_id
                and partner.company_registry in reg_by_value
            ):
                country_id = partner.country_id.id if partner.country_id else None
                company_id = partner.company_id.id if partner.company_id else None
                partner.same_company_registry_partner_id = _get_duplicate(
                    partner_id,
                    [partner.company_registry],
                    reg_by_value,
                    country_id,
                    company_id,
                    company_scoped=True,
                )
            else:
                partner.same_company_registry_partner_id = False

    @api.depends("complete_name", "country_id", "company_id", "parent_id")
    def _compute_possible_duplicates(self) -> None:
        matches = self._get_similar_named_partners()
        for partner in self:
            duplicates = matches.get(partner.id, self.browse())
            partner.duplicate_ids = duplicates
            partner.duplicate_count = len(duplicates)

    def _get_similar_named_partners(self) -> dict[int, ResPartner]:
        named = self.filtered(lambda partner: partner.complete_name)
        if not named or not self.env.registry.has_trigram:
            return {}
        recalled_by_index = self._get_similar_name_recall(named)
        if not recalled_by_index:
            return {}

        readable = self.browse(
            [
                candidate_id
                for recalled in recalled_by_index.values()
                for candidate_id in recalled
            ]
        )._filtered_access("read")
        readable.fetch(["complete_name", "parent_id", "company_id", "country_id"])
        readable_ids = set(readable._ids)

        threshold = self._get_similar_name_threshold()
        matches: dict[int, ResPartner] = {}
        for index, partner in enumerate(named):
            candidates = self.browse(
                [
                    candidate_id
                    for candidate_id in recalled_by_index.get(index, ())
                    if candidate_id in readable_ids
                ]
            )
            if not candidates:
                continue
            partner_id = partner._origin.id
            lowered = partner.complete_name.lower()
            shortest, longest = name_length_band(len(lowered), threshold)
            country_id = partner.country_id.id if partner.country_id else None
            company_id = partner.company_id.id if partner.company_id else None
            kept = self.browse()
            for other in candidates:
                name = (other.complete_name or "").lower()
                if not shortest <= len(name) <= longest:
                    continue
                if similarity_ratio(lowered, name) < threshold:
                    continue
                if _is_distinct_partner(other, partner_id, country_id, company_id):
                    kept |= other
            if kept:
                matches[partner.id] = kept
        _debug.perf.count(
            "similar_named_partners",
            named=len(named),
            recalled=sum(len(ids) for ids in recalled_by_index.values()),
            readable=len(readable_ids),
            matched=len(matches),
            threshold=threshold,
        )
        return matches

    def _get_similar_name_recall(self, named: ResPartner) -> dict[int, list[int]]:
        self.flush_model(["active", "complete_name"])
        self.env.cr.execute(
            SQL(
                "SELECT set_config('pg_trgm.similarity_threshold', %s, true)",
                str(self._get_similar_name_recall_threshold()),
            )
        )
        stored = SQL('candidate."complete_name"')
        if self.env.registry.has_unaccent == FunctionStatus.INDEXABLE:
            stored = self.env.registry.unaccent(stored)

        searched = SQL("source.name")
        if self.env.registry.has_unaccent == FunctionStatus.INDEXABLE:
            searched = self.env.registry.unaccent(searched)
        sources = SQL(", ").join(
            SQL("(%s::integer, %s::integer, %s::varchar)", index, id_ or 0, name)
            for index, (id_, name) in enumerate(
                (partner._origin.id, partner.complete_name) for partner in named
            )
        )
        self.env.cr.execute(  # noqa: E8501  built via SQL(), no user input
            SQL(
                """
                SELECT source.index, candidate.id
                  FROM (VALUES %s) AS source(index, id, name)
                 CROSS JOIN LATERAL (
                       SELECT candidate.id
                         FROM res_partner AS candidate
                        WHERE %s %% %s
                          AND candidate.active
                          AND candidate.complete_name IS NOT NULL
                          AND candidate.id != source.id
                        LIMIT %s
                       ) AS candidate
                """,
                sources,
                stored,
                searched,
                SIMILAR_NAME_RECALL_LIMIT,
            )
        )
        recalled_by_index: dict[int, list[int]] = defaultdict(list)
        for index, candidate_id in self.env.cr.fetchall():
            recalled_by_index[index].append(candidate_id)
        return recalled_by_index

    @api.model
    def _get_similar_name_threshold(self) -> float:
        raw = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(SIMILAR_NAME_THRESHOLD_PARAM)
        )
        try:
            value = float(raw)
        except TypeError, ValueError:
            return DEFAULT_SIMILAR_NAME_THRESHOLD
        if not 0 < value <= 1:
            return DEFAULT_SIMILAR_NAME_THRESHOLD
        return value

    @api.model
    def _get_similar_name_recall_threshold(self) -> float:
        return max(0.3, self._get_similar_name_threshold() - 0.2)

    def action_view_duplicates(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("%s and its possible duplicates", self.display_name),
            "res_model": "res.partner",
            "view_mode": "list,kanban,form",
            "domain": [("id", "in", (self | self.duplicate_ids).ids)],
            "context": {"create": False},
        }

    def _get_identifier(self, code: str) -> str | Literal[False]:
        self.check_singleton()
        identifier = self.identifier_ids.filtered(
            lambda i, code=code: i.type_id.code == code
        )[:1]
        if identifier:
            return identifier.value
        identifier_type = self.env["res.partner.identifier.type"]._get_type_by_code(
            code
        )
        if identifier_type.synced_with_commercial:
            commercial = self.commercial_partner_id
            if commercial != self:
                return commercial._get_identifier(code)
        return False

    def _update_identifier(self, code: str, value) -> None:
        self.check_singleton()
        identifier_type = self.env["res.partner.identifier.type"]._get_type_by_code(
            code
        )
        if not identifier_type:
            raise UserError(
                self.env._("There is no identifier type with code %(code)s.", code=code)
            )
        existing = self.identifier_ids.filtered(
            lambda i, identifier_type=identifier_type: i.type_id == identifier_type
        )
        _debug.lifecycle(
            "identifier_updated",
            partner=self.id,
            type=code,
            existing=len(existing),
            by="unlink" if not value else "write" if existing else "create",
        )
        if not value:
            existing.unlink()
            return
        if existing:
            existing[:1].value = value
            existing[1:].unlink()
        else:
            self.env["res.partner.identifier"].create(
                {
                    "partner_id": self.id,
                    "type_id": identifier_type.id,
                    "value": value,
                }
            )

    @api.depends_context("company")
    def _compute_vat_label(self) -> None:
        self.vat_label = self.env.company.country_id.vat_label or _("Tax ID")

    @api.depends("parent_id", "type")
    def _compute_type_address_label(self) -> None:
        for partner in self:
            if partner.type == "invoice":
                partner.type_address_label = _("Invoice Address")
            elif partner.type == "delivery":
                partner.type_address_label = _("Delivery Address")
            elif partner.type == "private":
                partner.type_address_label = _("Private Address")
            elif partner.type == "contact" and partner.parent_id:
                partner.type_address_label = _("Company Address")
            else:
                partner.type_address_label = _("Address")

    def _phone_get_numbers(self, fname=False):
        self.check_singleton()
        return self[fname] if fname else self.phone_ids

    def _phone_get_number(self, *types: str, fname=False):
        return self._phone_get_numbers(fname=fname)._primary(*types)

    @api.depends(
        lambda self: [*self._display_address_depends(), "commercial_company_name"]
    )
    def _compute_contact_address(self) -> None:
        for partner in self:
            partner.contact_address = partner._display_address()

    @api.depends("is_company", "parent_id.commercial_partner_id")
    def _compute_commercial_partner_id(self) -> None:
        for partner in self:
            if partner.is_company or not partner.parent_id:
                partner.commercial_partner_id = partner
            else:
                partner.commercial_partner_id = partner.parent_id.commercial_partner_id

    @api.depends("parent_id.is_company", "commercial_partner_id.name")
    def _compute_commercial_company_name(self) -> None:
        for partner in self:
            p = partner.commercial_partner_id
            partner.commercial_company_name = p.is_company and p.name

    def _compute_company_registry(self) -> None:
        for partner in self:
            partner.company_registry = partner.company_registry

    @api.depends("country_id.code")
    def _compute_company_registry_label(self) -> None:
        label_by_country = self._get_company_registry_labels()
        for partner in self:
            country_code = partner.country_id.code
            partner.company_registry_label = label_by_country.get(
                country_code, _("Company ID")
            )

    def _get_company_registry_labels(self) -> dict[str, str]:
        return {}

    def _compute_company_registry_placeholder(self) -> None:
        self.company_registry_placeholder = False

    @api.constrains("parent_id")
    def _check_parent_id(self) -> None:
        if self._has_cycle():
            raise ValidationError(_("You cannot create recursive Partner hierarchies."))

    @api.constrains("company_id")
    def _check_partner_company(self) -> None:
        partners = self.filtered(lambda p: p.is_company and p.company_id)
        companies = self.env["res.company"].search_fetch(
            [("partner_id", "in", partners.ids)], ["partner_id"]
        )
        for company in companies:
            if company != company.partner_id.company_id:
                raise ValidationError(
                    _(
                        "The company assigned to this partner does not match the company this partner represents."
                    )
                )

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if default.get("name"):
            return vals_list
        return [
            dict(vals, name=self.env._("%s (copy)", partner.name))
            for partner, vals in zip(self, vals_list, strict=True)
        ]

    @api.onchange("parent_id")
    def _onchange_parent_id(self) -> dict[str, Any] | None:
        if not self.parent_id:
            return None
        result = {}
        partner = self._origin
        if (partner.type or self.type) == "contact":
            if address_values := self.parent_id._prepare_address_vals():
                result["value"] = address_values
        return result

    @api.onchange("country_id")
    def _onchange_country_id(self) -> None:
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange("state_id")
    def _onchange_state_id(self) -> None:
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange("parent_id", "company_id")
    def _onchange_company_id(self) -> None:
        if self.parent_id:
            self.company_id = self.parent_id.company_id.id

    @api.depends("name", "email")
    def _compute_email_formatted(self) -> None:
        normalize_all = tools.email_normalize_all
        fmt = tools.formataddr
        for partner in self:
            email = partner.email
            if not email:
                partner.email_formatted = False
                continue
            emails_normalized = normalize_all(email)
            if emails_normalized:
                partner.email_formatted = fmt(
                    (partner.name or "", ",".join(emails_normalized))
                )
            elif "@" in email:
                partner.email_formatted = fmt((partner.name or "", email))
            else:
                partner.email_formatted = False

    @api.constrains("barcode")
    def _check_barcode_unicity(self) -> None:
        self.flush_model(["barcode"])
        cid = str(self.env.company.id)
        self.env.cr.execute(
            tools.SQL(
                "SELECT id, barcode ->> %(cid)s FROM res_partner"
                " WHERE id = ANY(%(ids)s) AND barcode ->> %(cid)s IS NOT NULL",
                cid=cid,
                ids=list(self.ids),
            )
        )
        ids_by_value: dict[str, list[int]] = defaultdict(list)
        for partner_id, value in self.env.cr.fetchall():
            ids_by_value[value].append(partner_id)
        if any(len(ids) > 1 for ids in ids_by_value.values()):
            _debug.logic("barcode_duplicate", company=cid, scope="batch")
            raise ValidationError(_("Another partner already has this barcode"))
        if not ids_by_value:
            return
        probes = tools.SQL(" OR ").join(
            tools.SQL(
                "barcode @> jsonb_build_object(%(cid)s::text, %(value)s::text)",
                cid=cid,
                value=value,
            )
            for value in ids_by_value
        )
        self.env.cr.execute(
            tools.SQL(
                "SELECT 1 FROM res_partner WHERE (%(probes)s) AND id != ALL(%(ids)s) LIMIT 1",
                probes=probes,
                ids=list(self.ids),
            )
        )
        if self.env.cr.fetchone():
            _debug.logic("barcode_duplicate", company=cid, scope="others")
            raise ValidationError(_("Another partner already has this barcode"))

    def _convert_fields_to_values(self, field_names: list[str]) -> dict[str, Any]:
        if any(self._fields[fname].type == "one2many" for fname in field_names):
            msg = "One2Many fields cannot be synchronized as part of `commercial_fields` or `address fields`"
            raise ValueError(msg)
        return self._convert_to_write({fname: self[fname] for fname in field_names})

    @api.model
    def _address_fields(self) -> list[str]:
        return list(ADDRESS_FIELDS)

    @api.model
    def _formatting_address_fields(self) -> list[str]:
        return self._address_fields()

    def _is_geolocation_stale(self, vals: dict[str, Any]) -> bool:
        written_address_fields = [field for field in ADDRESS_FIELDS if field in vals]
        if not written_address_fields:
            return False
        if all(field in vals for field in POSITION_FIELDS):
            return False
        for partner in self:
            for field_name in written_address_fields:
                current = partner[field_name]
                if self._fields[field_name].type == "many2one":
                    current = current.id
                if (current or False) != (vals[field_name] or False):
                    return True
        return False

    def _prepare_vals_whole_when_any_set(
        self, field_names: list[str]
    ) -> dict[str, Any]:
        if any(self[fname] for fname in field_names):
            return self._convert_fields_to_values(field_names)
        return {}

    def _prepare_vals_only_when_set(self, field_names: list[str]) -> dict[str, Any]:
        set_fields = [fname for fname in field_names if self[fname]]
        return self._convert_fields_to_values(set_fields) if set_fields else {}

    def _prepare_address_vals(self) -> dict[str, Any]:
        return self._prepare_vals_whole_when_any_set(self._address_fields())

    def _update_address(self, vals: dict[str, Any]) -> None:
        addr_vals = {key: vals[key] for key in self._address_fields() if key in vals}
        if addr_vals:
            super().write(addr_vals)

    @api.model
    def _commercial_fields(self) -> list[str]:
        return self._synced_commercial_fields() + [
            "company_registry",
            "industry_ids",
            "primary_industry_id",
        ]

    @api.model
    def _synced_commercial_fields(self) -> list[str]:
        return ["vat"]

    def _prepare_commercial_vals(self) -> dict[str, Any]:
        return self._prepare_vals_only_when_set(self._commercial_fields())

    def _prepare_commercial_vals_synced(self) -> dict[str, Any]:
        return self._prepare_vals_only_when_set(self._synced_commercial_fields())

    @api.model
    def _company_dependent_commercial_fields(self) -> list[str]:
        return [
            fname
            for fname in self._commercial_fields()
            if self._fields[fname].company_dependent
        ]

    def _sync_commercial_fields_from_company(self) -> None:
        commercial_partner = self.commercial_partner_id
        if commercial_partner != self:
            sync_vals = commercial_partner._prepare_commercial_vals()
            if sync_vals:
                self.write(sync_vals)
                self._sync_commercial_fields_to_descendants(list(sync_vals))
            self._sync_company_dependent_commercial_fields()

    def _get_stored_company_ids(self, field_names: list[str]) -> set[int]:
        record_ids = list({*self.ids, *self.commercial_partner_id.ids})
        if not record_ids:
            return set()
        self.flush_model(field_names)
        self.env.cr.execute(
            tools.SQL(
                "SELECT %(columns)s FROM res_partner WHERE id = ANY(%(ids)s)",
                columns=tools.SQL(", ").join(
                    tools.SQL.identifier(fname) for fname in field_names
                ),
                ids=record_ids,
            )
        )
        return {
            int(company_key)
            for row in self.env.cr.fetchall()
            for value in row
            if value
            for company_key in value
        }

    def _sync_company_dependent_commercial_fields(self) -> None:
        if not (fields_to_sync := self._company_dependent_commercial_fields()):
            return

        if not (company_ids := self._get_stored_company_ids(fields_to_sync)):
            return
        other_companies = (
            self.env["res.company"].sudo().search([("id", "in", sorted(company_ids))])
            - self.env.company
        )
        for company_sudo in other_companies:
            self_in_company = self.with_company(company_sudo)
            commercial_in_company = self_in_company.commercial_partner_id
            stale_fields = [
                fname
                for fname in fields_to_sync
                if any(
                    partner[fname] != commercial_in_company[fname]
                    for partner in self_in_company
                )
            ]
            if stale_fields:
                _debug.pipeline(
                    "commercial_fields_synced_in_company",
                    partners=self.ids,
                    company=company_sudo.id,
                    fields=stale_fields,
                )
                self_in_company.write(
                    commercial_in_company._convert_fields_to_values(stale_fields)
                )

    def _sync_commercial_fields_to_descendants(
        self, fields_to_sync: list[str] | None = None
    ) -> None:
        self.check_singleton()
        commercial_partner = self.commercial_partner_id
        if fields_to_sync is None:
            fields_to_sync = self._commercial_fields()
        descendants = self.browse()
        frontier = self.child_ids.filtered(lambda c: not c.is_company)
        while frontier:
            descendants |= frontier
            frontier = (frontier.child_ids - self - descendants).filtered(
                lambda c: not c.is_company
            )
        if descendants:
            sync_vals = commercial_partner._convert_fields_to_values(fields_to_sync)
            descendants_to_sync = descendants.filtered(
                lambda d: any(
                    d._fields[fname].convert_to_write(d[fname], d) != sync_vals[fname]
                    for fname in fields_to_sync
                )
            )
            _debug.pipeline(
                "commercial_fields_synced_to_descendants",
                partner=self.id,
                descendants=len(descendants),
                stale=len(descendants_to_sync),
                fields=list(fields_to_sync),
            )
            if descendants_to_sync:
                descendants_to_sync.write(sync_vals)

    def _fields_sync(self, values: dict[str, Any]) -> None:
        _debug.logic(
            "fields_sync",
            partner=self.id,
            parent=self.parent_id.id,
            type=self.type,
            fields=list(values),
        )
        self._sync_from_parent(values)
        self._sync_to_parent(values)
        self._sync_children(values)

    def _sync_from_parent(self, values: dict[str, Any]) -> None:
        if not (values.get("parent_id") or values.get("type") == "contact"):
            return
        if values.get("parent_id"):
            self.sudo()._sync_commercial_fields_from_company()
        if self.parent_id and self.type == "contact":
            if address_values := self.parent_id._prepare_address_vals():
                self._update_address(address_values)

    def _sync_to_parent(self, values: dict[str, Any]) -> None:
        if not self.parent_id:
            return
        address_fields = self._address_fields()
        if (
            self.type == "contact"
            and ("parent_id" in values or any(f in values for f in address_fields))
            and any(self[f] != self.parent_id[f] for f in address_fields)
            and (address_vals := self._prepare_address_vals())
        ):
            _debug.logic(
                "address_synced_to_parent", partner=self.id, parent=self.parent_id.id
            )
            self.parent_id.write(address_vals)
        synced_fields = self._synced_commercial_fields()
        if (
            self.commercial_partner_id != self
            and ("parent_id" in values or any(f in values for f in synced_fields))
            and any(self[f] != self.parent_id[f] for f in synced_fields)
            and (synced_vals := self._prepare_commercial_vals_synced())
        ):
            _debug.logic(
                "commercial_synced_to_parent",
                partner=self.id,
                parent=self.parent_id.id,
                fields=list(synced_vals),
            )
            self.parent_id.write(synced_vals)

    def _sync_children(self, values: dict[str, Any]) -> None:
        if self.commercial_partner_id == self:
            fields_to_sync = values.keys() & self._commercial_fields()
            if fields_to_sync:
                self.sudo()._sync_commercial_fields_to_descendants(fields_to_sync)
        address_fields = self._address_fields()
        if any(field in values for field in address_fields):
            contacts = self.child_ids.filtered(lambda c: c.type == "contact")
            _debug.logic(
                "address_synced_to_children", partner=self.id, contacts=len(contacts)
            )
            if contacts:
                contacts._update_address(values)

    def _update_parent_address(self) -> None:
        parent = self.parent_id
        address_fields = self._address_fields()
        if (
            (parent.is_company or not parent.parent_id)
            and any(self[f] for f in address_fields)
            and not any(parent[f] for f in address_fields)
            and len(parent.child_ids) == 1
        ):
            addr_vals = self._convert_fields_to_values(address_fields)
            _debug.logic("parent_address_filled", partner=self.id, parent=parent.id)
            parent._update_address(addr_vals)

    def _clean_website(self, website: str) -> str:
        url = urlsplit(website)
        if not url.scheme:
            if not url.netloc:
                url = url._replace(netloc=url.path, path="")
            website = urlunsplit(url._replace(scheme="http"))
        return website

    def _compute_is_public(self) -> None:
        self.is_public = False
        public_group = self.env.ref("base.group_public", raise_if_not_found=False)
        if not public_group:
            return
        public_partner_ids = {
            partner.id
            for (partner,) in self.env["res.users"]
            .sudo()
            .with_context(active_test=False)
            ._read_group(
                [
                    ("group_ids", "in", [public_group.id]),
                    ("partner_id", "in", self.ids),
                ],
                groupby=["partner_id"],
            )
        }
        if public_partner_ids:
            self.filtered(lambda p: p.id in public_partner_ids).is_public = True

    def _prepare_linked_user_error(self, users: ResUsers, operation: str) -> UserError:
        names = ", ".join(users.mapped("display_name"))
        if operation == "archive":
            lead = _("You cannot archive contacts linked to an active user.")
            remedy_self = _("You first need to archive their associated user.")
        else:
            lead = _("You cannot delete contacts linked to an active user.")
            remedy_self = _(
                "You should rather archive them after archiving their associated user."
            )
        if self.env["res.users"].sudo(False).has_access("write"):
            error_msg = _(
                "%(lead)s\n%(remedy)s\n\nLinked active users : %(names)s",
                lead=lead,
                remedy=remedy_self,
                names=names,
            )
            return RedirectWarning(error_msg, users._action_show(), _("Go to users"))
        return ValidationError(
            _(
                "%(lead)s\n%(remedy)s\n\nLinked active users :\n%(names)s",
                lead=lead,
                remedy=_(
                    "Ask an administrator to archive their associated user first."
                ),
                names=names,
            )
        )

    def write(self, vals: dict[str, Any]) -> bool:
        vals = dict(vals)
        if self._is_geolocation_stale(vals):
            vals["partner_latitude"] = False
            vals["partner_longitude"] = False
        if "active" in vals and not vals["active"]:
            self.invalidate_recordset(["user_ids"])
            users = (
                self.env["res.users"].sudo().search([("partner_id", "in", self.ids)])
            )
            if users:
                raise self._prepare_linked_user_error(users, "archive")
        if vals.get("website"):
            vals["website"] = self._clean_website(vals["website"])
        if vals.get("name"):
            banks_to_sync = self.with_context(active_test=False).bank_ids.filtered(
                lambda bank: bank.acc_holder_name == bank.partner_id.name
            )
            if banks_to_sync:
                banks_to_sync.acc_holder_name = vals["name"]

        sync_fields = (
            {"parent_id", "type"}
            | set(self._address_fields())
            | set(self._commercial_fields())
        )
        tracked_fields = [fname for fname in vals if fname in sync_fields]
        pre_values_list = [
            {fname: partner[fname] for fname in tracked_fields} for partner in self
        ]

        if "company_id" in vals:
            company_id = vals["company_id"]
            if company_id:
                company = self.env["res.company"].browse(company_id)
                for partner in self:
                    if partner.user_ids:
                        companies = {user.company_id for user in partner.user_ids}
                        if len(companies) > 1 or company not in companies:
                            raise UserError(
                                self.env._(
                                    "The selected company is not compatible with the companies of the related user(s)"
                                )
                            )
            children = self.with_context(active_test=False).search(
                [("parent_id", "in", self.ids)]
            )
            if children:
                children.write({"company_id": company_id})

        backing_ids = (
            self.sudo()
            .user_ids.filtered(lambda u: u._is_internal() and u.id != self.env.uid)
            .ids
        )
        if backing_ids:
            self.env["res.users"].browse(backing_ids).check_access("write")
        result = True
        if (
            "is_company" in vals
            and not self.env.su
            and self.env.user.has_group("base.group_partner_manager")
        ):
            result = super(ResPartner, self.sudo()).write(
                {"is_company": vals.get("is_company")}
            )
            del vals["is_company"]
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        result = result and super().write(vals)
        if {"lang", "tz"} & vals.keys() and self.sudo().with_context(
            active_test=False
        ).user_ids:
            self.env.registry.clear_cache()
        for partner, pre_values in zip(self, pre_values_list, strict=True):
            updated = {
                fname: vals[fname]
                for fname in tracked_fields
                if partner[fname] != pre_values[fname]
            }
            if updated:
                partner._fields_sync(updated)
        return result

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        vals_list = [dict(vals) for vals in vals_list]
        if self.env.context.get("import_file"):
            self._check_import_consistency(vals_list)
        for vals in vals_list:
            if vals.get("website"):
                vals["website"] = self._clean_website(vals["website"])
        partners = super().create(vals_list)
        partners_without_lang = partners.browse(
            partner.id
            for partner, values in zip(partners, vals_list, strict=True)
            if "lang" not in values
        )
        _debug.lifecycle(
            "create",
            count=len(partners),
            companies=sum(1 for vals in vals_list if vals.get("is_company")),
            with_parent=sum(1 for vals in vals_list if vals.get("parent_id")),
            without_lang=len(partners_without_lang),
            skip_sync=bool(self.env.context.get("_partners_skip_fields_sync")),
        )
        if partners_without_lang:
            partners_without_lang._update_lang_from_parent()

        if self.env.context.get("_partners_skip_fields_sync"):
            return partners

        missing_defaults_cache: dict[frozenset[str], list[str]] = {}
        for partner, vals in zip(partners, vals_list, strict=True):
            vals = self.env["res.partner"]._add_missing_default_values(
                vals, _missing_defaults_cache=missing_defaults_cache
            )
            partner._fields_sync(vals)
        return partners

    @api.ondelete(at_uninstall=False)
    def _unlink_except_user(self) -> None:
        users = self.env["res.users"].sudo().search([("partner_id", "in", self.ids)])
        if users:
            raise self._prepare_linked_user_error(users, "delete")

    def _load_records_create(self, vals_list: list[ValuesType]) -> Self:
        partners = super(
            ResPartner, self.with_context(_partners_skip_fields_sync=True)
        )._load_records_create(vals_list)

        groups = defaultdict(list)
        for partner, vals in zip(partners, vals_list, strict=True):
            cp_id = None
            if vals.get("parent_id") and partner.commercial_partner_id != partner:
                cp_id = partner.commercial_partner_id.id

            add_id = None
            if partner.parent_id and partner.type == "contact":
                add_id = partner.parent_id.id
            groups[(cp_id, add_id)].append(partner.id)

        for (cp_id, add_id), children in groups.items():
            to_write = {}
            if cp_id:
                to_write = self.sudo().browse(cp_id)._prepare_commercial_vals()
            if add_id:
                parent = self.browse(add_id)
                for f in self._address_fields():
                    v = parent[f]
                    if v:
                        to_write[f] = v.id if isinstance(v, models.BaseModel) else v
            if to_write:
                self.sudo().browse(children).write(to_write)

        _debug.pipeline(
            "load_records_create", partners=len(partners), groups=len(groups)
        )
        for partner, vals in zip(partners, vals_list, strict=True):
            partner._sync_children(vals)
            partner._update_parent_address()
        return partners

    def _create_parent_from_name(
        self, parent_name: str, additional_values: dict[str, Any] | None = None
    ) -> Self:
        self.check_singleton()
        if not parent_name:
            return self.browse()
        values = {
            "name": parent_name,
            "is_company": True,
            "vat": self.vat,
        }
        values.update(self._convert_fields_to_values(self._address_fields()))
        if additional_values:
            values.update(additional_values)
        parent_company = self._create_contact_parent_company(values)
        _debug.lifecycle(
            "parent_created_from_name",
            partner=self.id,
            parent=parent_company.id,
            children=len(self.child_ids),
        )
        self.write(
            {
                "parent_id": parent_company.id,
                "child_ids": [
                    Command.update(partner_id, {"parent_id": parent_company.id})
                    for partner_id in self.child_ids.ids
                ],
            }
        )
        return parent_company

    def _create_contact_parent_company(self, values: dict[str, Any]) -> Self:
        self.check_singleton()
        return self.create(values)

    def open_commercial_entity(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": self.commercial_partner_id.id,
            "target": "current",
        }

    @api.depends(
        lambda self: [
            "complete_name",
            "email",
            "vat",
            "commercial_company_name",
            *self._display_address_depends(),
        ]
    )
    @api.depends_context(
        "show_address",
        "partner_show_db_id",
        "show_email",
        "show_vat",
        "lang",
        "formatted_display_name",
        "partner_display_name_hide_company",
    )
    def _compute_display_name(self) -> None:
        type_description = dict(self._fields["type"]._description_selection(self.env))
        ctx = self.env.context
        ctx_get = ctx.get
        is_formatted = ctx_get("formatted_display_name")
        show_email = ctx_get("show_email")
        show_db_id = ctx_get("partner_show_db_id")
        show_address = ctx_get("show_address")
        show_vat = ctx_get("show_vat")
        ws_re = _RE_WHITESPACE_BEFORE_NEWLINE

        for partner in self:
            if is_formatted:
                name = partner.name or ""
                if partner.parent_id:
                    name = (
                        f"{partner.parent_id.name} \t "
                        f"--{partner.name or type_description.get(partner.type, '')}--"
                    )

                if show_email and partner.email:
                    name = f"{name} \t --{partner.email}--"
                elif show_db_id:
                    name = f"{name} \t --{partner.id}--"

            else:
                name = partner._get_complete_name(type_description)
                if show_db_id:
                    name = f"{name} ({partner.id})"
                if show_email and partner.email:
                    name = f"{name} <{partner.email}>"
                if show_address:
                    name = name + "\n" + partner._display_address(without_company=True)
                if show_vat and partner.vat:
                    if show_address:
                        name = f"{name} \n {partner.vat}"
                    else:
                        name = f"{name} - {partner.vat}"

            partner.display_name = ws_re.sub("\n", name).strip()

    @api.model
    def name_create(self, name: str) -> tuple[int, str]:
        default_type = self.env.context.get("default_type")
        if default_type and default_type not in self._fields["type"].get_values(
            self.env
        ):
            context = dict(self.env.context)
            context.pop("default_type")
            self = self.with_context(context)
        name, email_normalized = tools.parse_contact_from_email(name)
        if self.env.context.get("force_email") and not email_normalized:
            raise ValidationError(_("Couldn't create contact without email address!"))

        create_values = {self._rec_name: name or email_normalized}
        if email_normalized:
            create_values["email"] = email_normalized
        partner = self.create(create_values)
        return partner.id, partner.display_name

    @api.model
    def get_or_create(self, email: str, assert_valid_email: bool = False) -> Self:
        if not email:
            raise ValueError("An email is required for get_or_create to work")

        parsed_name, parsed_email_normalized = tools.parse_contact_from_email(email)
        if not parsed_email_normalized and assert_valid_email:
            raise ValueError(
                "A valid email is required for get_or_create to work properly."
            )

        if parsed_email_normalized:
            partners = self.search(
                [("email", "=ilike", tools.escape_psql(parsed_email_normalized))],
                limit=1,
            )
            if partners:
                _debug.logic("get_or_create", found=partners.id)
                return partners

        _debug.logic(
            "get_or_create", found=None, valid_email=bool(parsed_email_normalized)
        )
        create_values = {self._rec_name: parsed_name or parsed_email_normalized}
        if parsed_email_normalized:
            create_values["email"] = parsed_email_normalized
        return self.create(create_values)

    def address_get(self, adr_pref: list[str] | None = None) -> dict[str, int | bool]:
        adr_pref = set(adr_pref or [])
        if "contact" not in adr_pref:
            adr_pref.add("contact")
        result = {}
        if self:
            chains = []
            for partner in self:
                chain = [partner]
                seen_ids = {partner.id}
                current = partner
                while not current.is_company and current.parent_id:
                    current = current.parent_id
                    if current.id in seen_ids:
                        break
                    seen_ids.add(current.id)
                    chain.append(current)
                chains.append(chain)

            children_map = defaultdict(list)
            root_ids = [
                chain[-1].id for chain in chains if isinstance(chain[-1].id, int)
            ]
            if root_ids:
                nodes = self.with_context(active_test=False).search(
                    [("id", "child_of", root_ids), ("active", "=", True)]
                )
                nodes.fetch(["parent_id", "type", "is_company"])
                for node in nodes:
                    if node.parent_id:
                        children_map[node.parent_id.id].append(node)
                _debug.perf.count(
                    "address_get_tree_loaded",
                    partners=len(self),
                    roots=len(root_ids),
                    nodes=len(nodes),
                    types=sorted(adr_pref),
                )

            visited = set()
            for chain in chains:
                for current in chain:
                    stack = [current]
                    while stack:
                        record = stack.pop()
                        if record.id in visited:
                            continue
                        visited.add(record.id)
                        if record.type in adr_pref and not result.get(record.type):
                            result[record.type] = record.id
                        if len(result) == len(adr_pref):
                            return result
                        if isinstance(record.id, int):
                            children = children_map.get(record.id, ())
                        else:
                            children = record.child_ids
                        stack.extend(
                            reversed([c for c in children if not c.is_company])
                        )

        default = result.get("contact", self[:1].id or False)
        for adr_type in adr_pref:
            result[adr_type] = result.get(adr_type) or default
        return result

    @api.model
    def view_header_get(self, view_id: int | None, view_type: str) -> str | bool:
        if self.env.context.get("tag_id"):
            return _(
                "Partners: %(tag)s",
                tag=self.env["res.partner.tag"].browse(self.env.context["tag_id"]).name,
            )
        return super().view_header_get(view_id, view_type)

    @api.model
    def _get_default_address_format(self) -> str:
        return (
            "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"
        )

    @api.model
    def _get_address_format(self) -> str:
        return self.country_id.address_format or self._get_default_address_format()

    def _prepare_display_address(
        self, without_company: bool = False
    ) -> tuple[str, dict[str, str]]:
        address_format = self._get_address_format()
        args = defaultdict(
            str,
            {
                "state_code": self.state_id.code or "",
                "state_name": self.state_id.name or "",
                "country_code": self.country_id.code or "",
                "country_name": self._get_country_name(),
                "company_name": self.commercial_company_name or "",
            },
        )
        for field in self._formatting_address_fields():
            args[field] = self[field] or ""
        if without_company:
            args["company_name"] = ""
        elif self.commercial_company_name:
            address_format = "%(company_name)s\n" + address_format
        return address_format, args

    def _display_address(self, without_company: bool = False) -> str:
        address_format, args = self._prepare_display_address(without_company)
        try:
            return address_format % args
        except KeyError, ValueError:
            memo_key = (self.env.cr.dbname, address_format)
            if memo_key not in _FAILED_ADDRESS_FORMATS:
                _FAILED_ADDRESS_FORMATS.add(memo_key)
                _logger.warning(
                    "Invalid address format %r on country %r; falling back to"
                    " the default field order.",
                    address_format,
                    self.country_id.name or "?",
                )
            return " ".join(
                filter(
                    None,
                    (
                        args[key]
                        for key in (
                            "street",
                            "street2",
                            "city",
                            "state_name",
                            "zip",
                            "country_name",
                        )
                    ),
                )
            )

    def _display_address_depends(self) -> list[str]:
        return list(
            tools.unique(
                [
                    *self._formatting_address_fields(),
                    "country_id",
                    "commercial_company_name",
                    "state_id",
                ]
            )
        )

    @api.model
    def get_import_templates(self) -> list[dict[str, str]]:
        return [
            {
                "label": _("Import Template for Contacts"),
                "template": "/base/static/xls/contacts_import_template.xlsx",
            }
        ]

    @api.model
    def _check_import_consistency(self, vals_list: list[ValuesType]) -> None:
        States = self.env["res.country.state"]
        states_ids = {vals["state_id"] for vals in vals_list if vals.get("state_id")}
        state_info_by_id = {
            rec["id"]: rec
            for rec in States.search_read(
                [("id", "in", list(states_ids))], ["country_id", "code"]
            )
        }
        mismatches: list[tuple[ValuesType, tuple[str, int]]] = []
        for vals in vals_list:
            if not vals.get("state_id") or not vals.get("country_id"):
                continue
            state_info = state_info_by_id.get(vals["state_id"])
            if state_info is None:
                continue
            if state_info["country_id"][0] != vals["country_id"]:
                mismatches.append((vals, (state_info["code"], vals["country_id"])))
        if not mismatches:
            return

        mismatch_keys = {key for _vals, key in mismatches}
        all_codes = list({code for code, _country_id in mismatch_keys})
        all_country_ids = list({country_id for _code, country_id in mismatch_keys})
        state_by_key: dict[tuple[str, int], Any] = {}
        for state in States.search(
            [
                ("code", "in", all_codes),
                ("country_id", "in", all_country_ids),
            ]
        ):
            key = (state.code, state.country_id.id)
            if key in mismatch_keys:
                state_by_key.setdefault(key, state)

        _debug.pipeline(
            "import_state_country_realigned",
            records=len(vals_list),
            mismatches=len(mismatches),
            resolved=sum(1 for _vals, key in mismatches if key in state_by_key),
        )
        for vals, key in mismatches:
            matching = state_by_key.get(key)
            vals["state_id"] = matching.id if matching else False

    def _get_country_name(self) -> str:
        return self.country_id.name or ""

    def _get_all_addr(self) -> list[ValuesType]:
        self.check_singleton()
        return [
            {
                "contact_type": self.type,
                "street": self.street,
                "street2": self.street2,
                "zip": self.zip,
                "city": self.city,
                "state": self.state_id.code,
                "country": self.country_id.code,
            }
        ]
