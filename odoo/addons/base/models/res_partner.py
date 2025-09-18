import base64
import collections
import datetime
import re
import typing
from collections import defaultdict, deque
from typing import Any, Self
from urllib.parse import urlsplit, urlunsplit

from odoo import Command, _, api, fields, models, tools
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.libs.datetime.tz import all_timezones
from odoo.libs.datetime.tz import timezone as get_timezone
from odoo.orm._typing import ValuesType

if typing.TYPE_CHECKING:
    from .res_users import ResUsers


from .res_partner_format_address_mixin import ADDRESS_FIELDS

EU_EXTRA_VAT_CODES = {
    "GR": "EL",
    "GB": "XI",
}


def _find_duplicate(
    partner_id: int | bool,
    values: list[str],
    candidates_by_value: dict[str, list],
    country_id: int | None,
    company_id: int | None,
) -> Any:
    """Find first duplicate candidate matching the given criteria.

    Replaces per-partner ``search(domain, limit=1)`` calls with Python-only
    filtering on pre-fetched candidates.  Candidates are iterated in default
    model order (same as ``search`` would return), so the first match is
    equivalent to the original ``limit=1`` result.

    Filters replicate the original SQL domain:
    - ``("country_id", "in", [country_id, False])`` when *country_id* is set
    - ``("company_id", "in", [False, company_id])`` when *company_id* is set
    - ``("id", "!=", partner_id)``
    - ``"!", ("id", "child_of", partner_id)``
    """
    for value in values:
        for candidate in candidates_by_value.get(value, []):
            if candidate.id == partner_id:
                continue
            # Exclude descendants (replaces child_of domain negation)
            if partner_id and _is_descendant_of(candidate, partner_id):
                continue
            # Country filter — skip candidates with a different country
            if (
                country_id
                and candidate.country_id.id
                and candidate.country_id.id != country_id
            ):
                continue
            # Company filter — skip candidates with a different company
            if (
                company_id
                and candidate.company_id.id
                and candidate.company_id.id != company_id
            ):
                continue
            return candidate
    return False


def _is_descendant_of(candidate: Any, ancestor_id: int) -> bool:
    """Check if candidate is a descendant of ancestor_id via parent_id chain.

    Walks up the parent hierarchy (typically 1-2 hops for contacts).
    Parent records are batch-prefetched by the ORM, so this does not
    trigger per-call queries.  Includes a visited-set guard to prevent
    infinite loops if a cycle exists in the database.
    """
    seen = set()
    record = candidate
    while record := record.parent_id:
        if record.id == ancestor_id:
            return True
        if record.id in seen:
            return False
        seen.add(record.id)
    return False


@api.model
def _lang_get(self) -> list[tuple[str, str]]:
    return self.env["res.lang"].get_installed()


# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [
    (tz, tz)
    for tz in sorted(
        all_timezones(), key=lambda tz: tz if not tz.startswith("Etc/") else "_"
    )
]


def _tz_get(self) -> list[tuple[str, str]]:
    return _tzs


# Precompiled regex for collapsing whitespace before newlines in display names.
_RE_WHITESPACE_BEFORE_NEWLINE = re.compile(r"\s+\n")


class ResPartner(models.Model):
    _name = "res.partner"
    _description = "Contact"
    _inherit = [
        "format.address.mixin",
        "format.vat.label.mixin",
        "avatar.mixin",
        "properties.base.definition.mixin",
    ]
    _order = "complete_name ASC, id DESC"
    _rec_names_search = [
        "complete_name",
        "email",
        "ref",
        "vat",
        "company_registry",
    ]  # TODO vat must be sanitized the same way for storing/searching
    _allow_sudo_commands = False
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    # the partner types that must be added to a partner's complete name, like "Delivery"
    _complete_name_displayed_types = ("invoice", "delivery", "other")

    def _default_category(self) -> Self:
        return self.env["res.partner.category"].browse(
            self.env.context.get("category_id")
        )

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        """Add the company of the parent as default if we are creating a child partner."""
        values = super().default_get(fields)
        if "parent_id" in fields and values.get("parent_id"):
            parent = self.browse(values.get("parent_id"))
            values["company_id"] = parent.company_id.id
        # protection for `default_type` values leaking from menu action context (e.g. for crm's email)
        if "type" in fields and values.get("type"):
            if values["type"] not in self._fields["type"].get_values(self.env):
                values["type"] = None
        return values

    name = fields.Char(index=True, default_export_compatible=True)
    complete_name = fields.Char(
        compute="_compute_complete_name",
        store=True,
        index=True,
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
        context={"active_test": False},
    )
    ref = fields.Char(string="Reference", index=True)
    lang = fields.Selection(
        _lang_get,
        string="Language",
        compute="_compute_lang",
        readonly=False,
        store=True,
        help="All the emails and documents sent to this contact will be translated in this language.",
    )
    active_lang_count = fields.Integer(compute="_compute_active_lang_count")
    tz = fields.Selection(
        _tzs,
        string="Timezone",
        default=lambda self: self.env.context.get("tz"),
        help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
        "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
        "Anywhere else, time values are computed according to the time offset of your web client.",
    )

    tz_offset = fields.Char(compute="_compute_tz_offset", string="Timezone offset")
    # Warning: user_id is a Salesperson, not the inverse of partner_id in res.users.
    # For the latter, see user_ids and main_user_id.
    user_id: ResUsers = fields.Many2one(
        "res.users",
        string="Salesperson",
        compute="_compute_user_id",
        precompute=True,  # avoid queries post-create
        readonly=False,
        store=True,
        help="The internal user in charge of this contact.",
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
        compute="_compute_same_vat_partner_id",
        store=False,
    )
    same_company_registry_partner_id = fields.Many2one(
        "res.partner",
        string="Partner with same Company Registry",
        compute="_compute_same_vat_partner_id",
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
    bank_ids = fields.One2many(
        "res.partner.bank",
        "partner_id",
        string="Banks",
    )
    website = fields.Char("Website Link")
    comment = fields.Html(string="Notes")

    category_id = fields.Many2many(
        "res.partner.category",
        column1="partner_id",
        column2="category_id",
        string="Tags",
        default=_default_category,
    )
    active = fields.Boolean(default=True)
    employee = fields.Boolean(
        help="Check this box if this contact is an Employee.",
    )
    function = fields.Char(string="Job Position")
    type = fields.Selection(
        [
            ("contact", "Contact"),
            ("invoice", "Invoice"),
            ("delivery", "Delivery"),
            ("other", "Other"),
        ],
        string="Address Type",
        default="contact",
    )
    type_address_label = fields.Char(
        "Address Type Description",
        compute="_compute_type_address_label",
    )
    # address fields
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
    country_code = fields.Char(related="country_id.code", string="Country Code")
    partner_latitude = fields.Float(string="Geo Latitude", digits=(10, 7))
    partner_longitude = fields.Float(string="Geo Longitude", digits=(10, 7))
    email = fields.Char()
    email_formatted = fields.Char(
        "Formatted Email",
        compute="_compute_email_formatted",
        help='Format email address "Name <email@domain>"',
    )
    phone = fields.Char()
    is_company = fields.Boolean(
        string="Is a Company",
        default=False,
        help="Check if the contact is a company, otherwise it is a person",
    )
    is_public = fields.Boolean(
        compute="_compute_is_public",
        compute_sudo=True,
    )
    industry_id = fields.Many2one(
        "res.partner.industry",
        "Industry",
    )
    # company_type is only an interface field, do not use it in business logic
    company_type = fields.Selection(
        string="Company Type",
        selection=[("person", "Person"), ("company", "Company")],
        compute="_compute_company_type",
        inverse="_write_company_type",
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        index=True,
    )
    color = fields.Integer(string="Color Index", default=0)
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
    partner_share = fields.Boolean(
        "Share Partner",
        compute="_compute_partner_share",
        store=True,
        help="Either customer (not a user), either shared user. Indicated the current partner is a customer without "
        "access or with a limited access created for sharing data.",
    )
    contact_address = fields.Char(
        compute="_compute_contact_address",
        string="Complete Address",
    )

    # technical field used for managing commercial fields
    commercial_partner_id = fields.Many2one(
        "res.partner",
        string="Commercial Entity",
        compute="_compute_commercial_partner",
        store=True,
        recursive=True,
        index=True,
    )
    commercial_company_name = fields.Char(
        "Company Name Entity",
        compute="_compute_commercial_company_name",
        store=True,
    )
    company_name = fields.Char("Company Name")
    barcode = fields.Char(
        help="Use a barcode to identify this contact.",
        copy=False,
        company_dependent=True,
    )

    # hack to allow using plain browse record in qweb views, and used in ir.qweb.field.contact
    self = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_get_ids",
    )
    application_statistics = fields.Json(
        string="Stats",
        compute="_compute_application_statistics",
    )

    def _compute_application_statistics(self) -> None:
        result = self._compute_application_statistics_hook()
        for p in self:
            p.application_statistics = result.get(p.id, [])

    def _compute_application_statistics_hook(self) -> dict[int, list]:
        """Hook for override, as overriding compute method does not update
        cache accordingly. All overrides receive False instead of previously
        assigned value."""
        return defaultdict(list)

    _check_name = models.Constraint(
        "CHECK( (type='contact' AND name IS NOT NULL) or (type!='contact') )",
        "Contacts require a name",
    )

    def _get_street_split(self) -> dict[str, str]:
        self.ensure_one()
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

    def _compute_avatar(self, avatar_field: str, image_field: str) -> None:
        partners_with_internal_user = self.filtered(
            lambda partner: partner.user_ids - partner.user_ids.filtered("share")
            or partner.type == "contact"
        )
        super(ResPartner, partners_with_internal_user)._compute_avatar(
            avatar_field, image_field
        )
        partners_without_image = (self - partners_with_internal_user).filtered(
            lambda p: not p[image_field]
        )
        for _path, group in tools.groupby(
            partners_without_image,
            key=lambda p: p._avatar_get_placeholder_path(),
        ):
            group_partners = self.env["res.partner"].concat(*group)
            group_partners[avatar_field] = base64.b64encode(
                group_partners[0]._avatar_get_placeholder()
            )

        for partner in self - partners_with_internal_user - partners_without_image:
            partner[avatar_field] = partner[image_field]

    def _avatar_get_placeholder_path(self) -> str:
        if self.is_company:
            return "base/static/img/company_image.png"
        if self.type == "delivery":
            return "base/static/img/truck.png"
        if self.type == "invoice":
            return "base/static/img/bill.png"
        if self.type == "other":
            return "base/static/img/puzzle.png"
        return super()._avatar_get_placeholder_path()

    def _get_complete_name(self, type_description: dict[str, str] | None = None) -> str:
        """Build the full display name for a single partner.

        :param type_description: Pre-computed ``{type_key: label}`` mapping.
            When *None*, the mapping is built on-the-fly (backward compat).
        """
        self.ensure_one()

        if type_description is None:
            type_description = dict(
                self._fields["type"]._description_selection(self.env)
            )

        name = self.name or ""
        if self.company_name or self.parent_id:
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
        "company_name",
        "commercial_company_name",
    )
    def _compute_complete_name(self) -> None:
        type_description = dict(self._fields["type"]._description_selection(self.env))
        # Use with_context({}) to strip context keys that affect display_name
        # (show_address, show_email, etc.) — but only create one proxy.
        clean_self = self.with_context({}) if self.env.context else self
        for partner in clean_self:
            partner.complete_name = partner._get_complete_name(type_description)

    @api.depends("parent_id")
    def _compute_lang(self) -> None:
        """While creating / updating child contact, take the parent lang by
        default if any. 0therwise, fallback to default context / DB lang"""
        for partner in self.filtered("parent_id"):
            partner.lang = (
                partner.parent_id.lang
                or self.default_get(["lang"]).get("lang")
                or self.env.lang
            )

    @api.depends("lang")
    def _compute_active_lang_count(self) -> None:
        lang_count = len(self.env["res.lang"].get_installed())
        for partner in self:
            partner.active_lang_count = lang_count

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
        """Synchronize sales rep with parent if partner is a person"""
        for partner in self.filtered(
            lambda partner: not partner.user_id
            and partner.company_type == "person"
            and partner.parent_id.user_id
        ):
            partner.user_id = partner.parent_id.user_id

    @api.depends_context("uid")
    @api.depends("user_ids.active", "user_ids.share")
    def _compute_main_user_id(self) -> None:
        """Determine the main user for each partner.

        Batch-fetches all active users linked to the partners in a single
        query, then selects the best match (prefer internal over share,
        smallest id) in Python.  Users are sorted at SQL level so the first
        match per partner is always the best — no per-partner ``min()`` needed.
        """
        Users = self.env["res.users"].sudo()
        current_user = self.env.user
        current_partner_id = current_user.partner_id.id
        root_partner_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "base.partner_root"
        )
        root_user = Users.browse(
            self.env["ir.model.data"]._xmlid_to_res_id("base.user_root")
        )

        # Single query: fetch all active users sorted by (share ASC, id ASC).
        # share=False (internal) sorts before share=True (portal), then
        # smallest id wins — so the first user per partner is always the best.
        best_user: dict[int, object] = {}
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

    @api.depends("user_ids.share", "user_ids.active")
    def _compute_partner_share(self) -> None:
        """Batch-determine which partners have internal (non-share) users."""
        super_partner = self.env["res.users"].browse(api.SUPERUSER_ID).partner_id
        if super_partner in self:
            super_partner.partner_share = False

        partners = self - super_partner
        if not partners:
            return

        # Default: all partners are "share" (external / no user)
        partners.partner_share = True

        # Single query: find partner_ids that have at least one internal user
        internal_partner_ids = {
            partner.id
            for (partner,) in self.env["res.users"]._read_group(
                [("partner_id", "in", partners.ids), ("share", "=", False)],
                groupby=["partner_id"],
            )
        }
        if internal_partner_ids:
            partners.filtered(lambda p: p.id in internal_partner_ids).partner_share = (
                False
            )

    @api.depends(
        "vat",
        "company_id",
        "company_registry",
        "country_id.country_group_codes",
        "country_id.code",
    )
    def _compute_same_vat_partner_id(self) -> None:
        """Detect duplicate VAT/company_registry with batch pre-fetching.

        Instead of N individual search() calls (one per partner), fetches all
        candidate records in 1-2 bulk queries and matches in Python.
        """
        # active_test=False: deactivated partners should still flag duplicates
        Partner = self.with_context(active_test=False).sudo()

        # Phase 1: Collect all VAT variants and registries across the batch.
        # Memoize per-partner VAT variant lists to avoid recomputing in Phase 4.
        all_vats = set()
        all_registries = set()
        vat_variants: dict[int, list[str]] = {}
        for partner in self:
            if partner.vat and len(partner.vat) != 1 and not partner.parent_id:
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

        # Phase 2: Quick existence check — skip batch fetch when values are
        # unique in the DB (common case for imports with unique values)
        existing_vats = set()
        if all_vats:
            existing_vats = {
                vat
                for (vat,) in Partner._read_group(
                    [("vat", "in", list(all_vats))],
                    groupby=["vat"],
                )
            }
        existing_registries = set()
        if all_registries:
            existing_registries = {
                reg
                for (reg,) in Partner._read_group(
                    [("company_registry", "in", list(all_registries))],
                    groupby=["company_registry"],
                )
            }

        # Phase 3: Batch-fetch ALL candidate records (replaces N search() calls)
        # Candidates are indexed by field value for O(1) lookup per partner.
        vat_by_value: dict[str, list] = defaultdict(list)
        if existing_vats:
            for c in Partner.search_fetch(
                [("vat", "in", list(existing_vats))],
                ["vat", "parent_id", "company_id", "country_id"],
            ):
                vat_by_value[c.vat].append(c)

        reg_by_value: dict[str, list] = defaultdict(list)
        if existing_registries:
            for c in Partner.search_fetch(
                [("company_registry", "in", list(existing_registries))],
                ["company_registry", "parent_id", "company_id"],
            ):
                reg_by_value[c.company_registry].append(c)

        # Phase 4: Python-only matching (0 additional SQL queries).
        # Reuses memoized VAT variants from Phase 1.
        for partner in self:
            partner_id = partner._origin.id
            vats = vat_variants.get(partner.id)

            if vats and existing_vats.intersection(vats):
                country_id = partner.country_id.id if partner.country_id else None
                company_id = partner.company_id.id if partner.company_id else None
                partner.same_vat_partner_id = _find_duplicate(
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
                and partner.company_registry in existing_registries
            ):
                company_id = partner.company_id.id if partner.company_id else None
                partner.same_company_registry_partner_id = _find_duplicate(
                    partner_id,
                    [partner.company_registry],
                    reg_by_value,
                    None,
                    company_id,
                )
            else:
                partner.same_company_registry_partner_id = False

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
            elif partner.type == "contact" and partner.parent_id:
                partner.type_address_label = _("Company Address")
            else:
                partner.type_address_label = _("Address")

    @api.depends(lambda self: self._display_address_depends())
    def _compute_contact_address(self) -> None:
        for partner in self:
            partner.contact_address = partner._display_address()

    def _compute_get_ids(self) -> None:
        for partner in self:
            partner.self = partner.id

    @api.depends("is_company", "parent_id.commercial_partner_id")
    def _compute_commercial_partner(self) -> None:
        for partner in self:
            if partner.is_company or not partner.parent_id:
                partner.commercial_partner_id = partner
            else:
                partner.commercial_partner_id = partner.parent_id.commercial_partner_id

    @api.depends("company_name", "parent_id.is_company", "commercial_partner_id.name")
    def _compute_commercial_company_name(self) -> None:
        for partner in self:
            p = partner.commercial_partner_id
            partner.commercial_company_name = (
                p.is_company and p.name
            ) or partner.company_name

    def _compute_company_registry(self) -> None:
        # exists to allow overrides
        for company in self:
            company.company_registry = company.company_registry

    @api.depends("country_id.code")
    def _compute_company_registry_label(self) -> None:
        label_by_country = self._get_company_registry_labels()
        for company in self:
            country_code = company.country_id.code
            company.company_registry_label = label_by_country.get(
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
        """
        Check that for every partner which has a company,
        if there exists a company linked to that partner,
        the company_id set on the partner is that company
        """
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
    def onchange_parent_id(self) -> dict[str, Any] | None:
        # return values in result, as this method is used by _fields_sync()
        if not self.parent_id:
            return None
        result = {}
        partner = self._origin
        if (partner.type or self.type) == "contact":
            # for contacts: copy the parent address, if set (aka, at least one
            # value is set in the address: otherwise, keep the one from the
            # contact)
            if address_values := self.parent_id._get_address_values():
                result["value"] = address_values
        return result

    @api.onchange("country_id")
    def _onchange_country_id(self) -> None:
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange("state_id")
    def _onchange_state(self) -> None:
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange("parent_id", "company_id")
    def _onchange_company_id(self) -> None:
        if self.parent_id:
            self.company_id = self.parent_id.company_id.id

    @api.depends("name", "email")
    def _compute_email_formatted(self) -> None:
        """Compute formatted email for partner, using formataddr.

        Handles edge cases:
          * double format: strips formatting if email is already formatted
          * multi emails: joins normalized addresses (some servers accept this)
          * invalid email: keeps raw value for debugging at mail level
          * void email: email_formatted is False
        """
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
            else:
                partner.email_formatted = fmt((partner.name or "", email))

    @api.depends("is_company")
    def _compute_company_type(self) -> None:
        for partner in self:
            partner.company_type = "company" if partner.is_company else "person"

    def _write_company_type(self) -> None:
        for partner in self:
            partner.is_company = partner.company_type == "company"

    @api.onchange("company_type")
    def onchange_company_type(self) -> None:
        self.is_company = self.company_type == "company"

    @api.constrains("barcode")
    def _check_barcode_unicity(self) -> None:
        """Check barcode uniqueness with a single search instead of N search_counts.

        Note: barcode is company_dependent (JSONB), so _read_group groupby
        is not supported — we use search_fetch + Python counting instead.
        """
        barcodes = [p.barcode for p in self if p.barcode]
        if not barcodes:
            return
        partners_with_barcodes = self.env["res.partner"].search_fetch(
            [("barcode", "in", barcodes)],
            ["barcode"],
        )
        seen = set()
        for partner in partners_with_barcodes:
            if partner.barcode in seen:
                raise ValidationError(_("Another partner already has this barcode"))
            seen.add(partner.barcode)

    def _convert_fields_to_values(self, field_names: list[str]) -> dict[str, Any]:
        """Returns dict of write() values for synchronizing ``field_names``"""
        if any(self._fields[fname].type == "one2many" for fname in field_names):
            raise AssertionError(
                _(
                    "One2Many fields cannot be synchronized as part of `commercial_fields` or `address fields`"
                )
            )
        return self._convert_to_write({fname: self[fname] for fname in field_names})

    @api.model
    def _address_fields(self) -> list[str]:
        """Returns the list of address fields that are synced from the parent."""
        return list(ADDRESS_FIELDS)

    @api.model
    def _formatting_address_fields(self) -> list[str]:
        """Returns the list of address fields usable to format addresses."""
        return self._address_fields()

    def _get_address_values(self) -> dict[str, Any]:
        """Get address values from record if at least one value is set. Otherwise
        it is considered empty and nothing is returned."""
        address_fields = self._address_fields()
        if any(self[key] for key in address_fields):
            return self._convert_fields_to_values(address_fields)
        return {}

    def _update_address(self, vals: dict[str, Any]) -> None:
        """Filter values from vals that are liked to address definition, and
        update recordset using super().write to avoid loops and side effects
        due to synchronization of address fields through partner hierarchy."""
        addr_vals = {key: vals[key] for key in self._address_fields() if key in vals}
        if addr_vals:
            super().write(addr_vals)

    @api.model
    def _commercial_fields(self) -> list[str]:
        """Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. These fields are meant to be hidden on
        partners that aren't `commercial entities` themselves, or synchronized
        at update (if present in _synced_commercial_fields), and will be
        delegated to the parent `commercial entity`. The list is meant to be
        extended by inheriting classes."""
        return self._synced_commercial_fields() + [
            "company_registry",
            "industry_id",
        ]

    @api.model
    def _synced_commercial_fields(self) -> list[str]:
        """Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. When modified on a children, update is
        propagated until the commercial entity."""
        return ["vat"]

    def _get_commercial_values(self) -> dict[str, Any]:
        """Get commercial values from record. Return only set values, as they
        are considered individually, and only set values should be taken into
        account."""
        set_commercial_fields = [
            fname for fname in self._commercial_fields() if self[fname]
        ]
        if set_commercial_fields:
            return self._convert_fields_to_values(set_commercial_fields)
        return {}

    def _get_synced_commercial_values(self) -> dict[str, Any]:
        """Get synchronized commercial values from ercord. Return only set values
        as for other commercial values."""
        set_synced_fields = [
            fname for fname in self._synced_commercial_fields() if self[fname]
        ]
        if set_synced_fields:
            return self._convert_fields_to_values(set_synced_fields)
        return {}

    @api.model
    def _company_dependent_commercial_fields(self) -> list[str]:
        return [
            fname
            for fname in self._commercial_fields()
            if self._fields[fname].company_dependent
        ]

    def _commercial_sync_from_company(self) -> None:
        """Handle sync of commercial fields when a new parent commercial entity is set,
        as if they were related fields"""
        commercial_partner = self.commercial_partner_id
        if commercial_partner != self:
            sync_vals = commercial_partner._get_commercial_values()
            if sync_vals:
                self.write(sync_vals)
                self._commercial_sync_to_descendants()
            self._company_dependent_commercial_sync()

    def _company_dependent_commercial_sync(self) -> None:
        """Propagate sync of company-dependent commercial fields to other companies."""
        if not (fields_to_sync := self._company_dependent_commercial_fields()):
            return

        all_companies = self.env["res.company"].sudo().search([])
        other_companies = all_companies - self.env.company
        for company_sudo in other_companies:
            self_in_company = self.with_company(company_sudo)
            self_in_company.write(
                self_in_company.commercial_partner_id._convert_fields_to_values(
                    fields_to_sync
                )
            )

    def _commercial_sync_to_descendants(
        self, fields_to_sync: list[str] | None = None
    ) -> None:
        """Handle sync of commercial fields to descendants"""
        commercial_partner = self.commercial_partner_id
        if fields_to_sync is None:
            fields_to_sync = self._commercial_fields()
        sync_vals = commercial_partner._convert_fields_to_values(fields_to_sync)
        sync_children = self.child_ids.filtered(lambda c: not c.is_company)
        for child in sync_children:
            child._commercial_sync_to_descendants(fields_to_sync)
        sync_children.write(sync_vals)

    def _fields_sync(self, values: dict[str, Any]) -> None:
        """Sync commercial fields and address fields from company and to children.
        Also synchronize address to parent. This somehow mimics related fields
        to the parent, with more control. This method should be called after
        updating values in cache e.g. self should contain new values.

        :param dict[str, Any] values: updated values, triggering sync
        """
        # 1. From UPSTREAM: sync from parent
        if values.get("parent_id") or values.get("type") == "contact":
            # 1a. Commercial fields: sync if parent changed
            if values.get("parent_id"):
                self.sudo()._commercial_sync_from_company()
            # 1b. Address fields: sync if parent or use_parent changed *and* both are now set
            if self.parent_id and self.type == "contact":
                if address_values := self.parent_id._get_address_values():
                    self._update_address(address_values)

        # 2. To UPSTREAM: sync parent address, as well as editable synchronized commercial fields
        address_to_upstream = (
            # parent is set, potential address update as contact address = parent address
            bool(self.parent_id)
            and bool(self.type == "contact")
            and
            # address updated, or parent updated
            (
                any(field in values for field in self._address_fields())
                or "parent_id" in values
            )
            and
            # something is actually updated
            any(
                self[fname] != self.parent_id[fname] for fname in self._address_fields()
            )
        )
        if address_to_upstream:
            new_address = self._get_address_values()
            self.parent_id.write(new_address)  # is going to trigger _fields_sync again
        commercial_to_upstream = (
            # has a parent and is not a commercial entity itself
            bool(self.parent_id)
            and (self.commercial_partner_id != self)
            and
            # actually updated, or parent updated
            (
                any(field in values for field in self._synced_commercial_fields())
                or "parent_id" in values
            )
            and
            # something is actually updated
            any(
                self[fname] != self.parent_id[fname]
                for fname in self._synced_commercial_fields()
            )
        )
        if commercial_to_upstream:
            new_synced_commercials = self._get_synced_commercial_values()
            self.parent_id.write(new_synced_commercials)

        # 3. To DOWNSTREAM: sync children
        self._children_sync(values)

    def _children_sync(self, values: dict[str, Any]) -> None:
        if not self.child_ids:
            return
        # 2a. Commercial Fields: sync if commercial entity
        if self.commercial_partner_id == self:
            fields_to_sync = values.keys() & self._commercial_fields()
            self.sudo()._commercial_sync_to_descendants(fields_to_sync)
        # 2b. Address fields: sync if address changed
        address_fields = self._address_fields()
        if any(field in values for field in address_fields):
            contacts = self.child_ids.filtered(lambda c: c.type == "contact")
            contacts._update_address(values)

    def _handle_first_contact_creation(self) -> None:
        """On creation of first contact for a company (or root) that has no address, assume contact address
        was meant to be company address"""
        parent = self.parent_id
        address_fields = self._address_fields()
        if (
            (parent.is_company or not parent.parent_id)
            and any(self[f] for f in address_fields)
            and not any(parent[f] for f in address_fields)
            and len(parent.child_ids) == 1
        ):
            addr_vals = self._convert_fields_to_values(address_fields)
            parent._update_address(addr_vals)

    def _clean_website(self, website: str) -> str:
        url = urlsplit(website)
        if not url.scheme:
            if not url.netloc:
                url = url._replace(netloc=url.path, path="")
            website = urlunsplit(url._replace(scheme="http"))
        return website

    def _compute_is_public(self) -> None:
        """Detect public partners via batch lookup instead of per-partner user_ids.

        Uses a single ``_read_group`` on ``res.users`` joining through the
        public group relation, avoiding intermediate record loads.
        """
        self.is_public = False
        public_group = self.env.ref("base.group_public", raise_if_not_found=False)
        if not public_group:
            return
        # Single query: find which of our partners are linked to a user in the
        # public group.  active_test=False because the public user is archived.
        public_partner_ids = {
            partner.id
            for (partner,) in self.env["res.users"]
            .sudo()
            .with_context(active_test=False)
            ._read_group(
                [
                    ("group_ids", "in", public_group.id),
                    ("partner_id", "in", self.ids),
                ],
                groupby=["partner_id"],
            )
        }
        if public_partner_ids:
            self.filtered(lambda p: p.id in public_partner_ids).is_public = True

    def write(self, vals: dict[str, Any]) -> bool:
        if vals.get("active") is False:
            # DLE: It should not be necessary to modify this to make work the ORM. The problem was just the recompute
            # of partner.user_ids when you create a new user for this partner, see test test_70_archive_internal_partners
            # You modified it in a previous commit, see original commit of this:
            # https://github.com/odoo/odoo/commit/9d7226371730e73c296bcc68eb1f856f82b0b4ed
            #
            # RCO: when creating a user for partner, the user is automatically added in partner.user_ids.
            # This is wrong if the user is not active, as partner.user_ids only returns active users.
            # Hence this temporary hack until the ORM updates inverse fields correctly.
            self.invalidate_recordset(["user_ids"])
            users = (
                self.env["res.users"].sudo().search([("partner_id", "in", self.ids)])
            )
            if users:
                if self.env["res.users"].sudo(False).has_access("write"):
                    error_msg = _(
                        "You cannot archive contacts linked to an active user.\n"
                        "You first need to archive their associated user.\n\n"
                        "Linked active users : %(names)s",
                        names=", ".join([u.display_name for u in users]),
                    )
                    action_error = users._action_show()
                    raise RedirectWarning(error_msg, action_error, _("Go to users"))
                raise ValidationError(
                    _(
                        "You cannot archive contacts linked to an active user.\n"
                        "Ask an administrator to archive their associated user first.\n\n"
                        "Linked active users :\n%(names)s",
                        names=", ".join([u.display_name for u in users]),
                    )
                )
        if vals.get("website"):
            vals["website"] = self._clean_website(vals["website"])
        if vals.get("parent_id"):
            vals["company_name"] = False
        if vals.get("name"):
            for partner in self:
                for bank in partner.bank_ids:
                    if bank.acc_holder_name == partner.name:
                        bank.acc_holder_name = vals["name"]

        # filter to keep only really updated values -> field synchronize goes through
        # partner tree and we should avoid infinite loops in case same value is
        # updated due to cycles. Use case: updating a property field, which updated
        # a computed field, which has an inverse writing the same value on property
        # field. Yay.
        pre_values_list = [
            {fname: partner[fname] for fname in vals} for partner in self
        ]

        # res.partner must only allow to set the company_id of a partner if it
        # is the same as the company of all users that inherit from this partner
        # (this is to allow the code from res_users to write to the partner!) or
        # if setting the company_id to False (this is compatible with any user
        # company)
        if "company_id" in vals:
            company_id = vals["company_id"]
            for partner in self:
                if company_id and partner.user_ids:
                    company = self.env["res.company"].browse(company_id)
                    companies = {user.company_id for user in partner.user_ids}
                    if len(companies) > 1 or company not in companies:
                        raise UserError(
                            self.env._(
                                "The selected company is not compatible with the companies of the related user(s)"
                            )
                        )
                if partner.child_ids:
                    partner.child_ids.write({"company_id": company_id})
        result = True
        # To write in SUPERUSER on field is_company and avoid access rights problems.
        if (
            "is_company" in vals
            and not self.env.su
            and self.env.user.has_group("base.group_partner_manager")
        ):
            result = super(ResPartner, self.sudo()).write(
                {"is_company": vals.get("is_company")}
            )
            del vals["is_company"]
        result = result and super().write(vals)
        for partner, pre_values in zip(self, pre_values_list, strict=True):
            if internal_users := partner.user_ids.filtered(
                lambda u: u._is_internal() and u != self.env.user
            ):
                internal_users.check_access("write")
            updated = {
                fname: fvalue
                for fname, fvalue in vals.items()
                if partner[fname] != pre_values[fname]
            }
            if updated:
                partner._fields_sync(updated)
        return result

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        if self.env.context.get("import_file"):
            self._check_import_consistency(vals_list)
        for vals in vals_list:
            if vals.get("website"):
                vals["website"] = self._clean_website(vals["website"])
            if vals.get("parent_id"):
                vals["company_name"] = False
        partners = super().create(vals_list)
        # due to ir.default, compute is not called as there is a default value
        # hence calling the compute manually
        for partner, values in zip(partners, vals_list, strict=True):
            if "lang" not in values and partner.parent_id:
                partner._compute_lang()

        if self.env.context.get("_partners_skip_fields_sync"):
            return partners

        for partner, vals in zip(partners, vals_list, strict=True):
            vals = self.env["res.partner"]._add_missing_default_values(vals)
            partner._fields_sync(vals)
        return partners

    @api.ondelete(at_uninstall=False)
    def _unlink_except_user(self) -> None:
        users = self.env["res.users"].sudo().search([("partner_id", "in", self.ids)])
        if not users:
            return  # no linked user, operation is allowed
        if self.env["res.users"].sudo(False).has_access("write"):
            error_msg = _(
                "You cannot delete contacts linked to an active user.\n"
                "You should rather archive them after archiving their associated user.\n\n"
                "Linked active users : %(names)s",
                names=", ".join([u.display_name for u in users]),
            )
            action_error = users._action_show()
            raise RedirectWarning(error_msg, action_error, _("Go to users"))
        raise ValidationError(
            _(
                "You cannot delete contacts linked to an active user.\n"
                "Ask an administrator to archive their associated user first.\n\n"
                "Linked active users :\n%(names)s",
                names=", ".join([u.display_name for u in users]),
            )
        )

    def _load_records_create(self, vals_list: list[ValuesType]) -> Self:
        partners = super(
            ResPartner, self.with_context(_partners_skip_fields_sync=True)
        )._load_records_create(vals_list)

        # batch up first part of _fields_sync
        # group partners by commercial_partner_id (if not self) and parent_id (if type == contact)
        groups = collections.defaultdict(list)
        for partner, vals in zip(partners, vals_list, strict=True):
            cp_id = None
            if vals.get("parent_id") and partner.commercial_partner_id != partner:
                cp_id = partner.commercial_partner_id.id

            add_id = None
            if partner.parent_id and partner.type == "contact":
                add_id = partner.parent_id.id
            groups[(cp_id, add_id)].append(partner.id)

        for (cp_id, add_id), children in groups.items():
            # values from parents (commercial, regular) written to their common children
            to_write = {}
            # commercial fields from commercial partner
            if cp_id:
                to_write = self.browse(cp_id)._convert_fields_to_values(
                    self._commercial_fields()
                )
            # address fields from parent
            if add_id:
                parent = self.browse(add_id)
                for f in self._address_fields():
                    v = parent[f]
                    if v:
                        to_write[f] = v.id if isinstance(v, models.BaseModel) else v
            if to_write:
                self.sudo().browse(children).write(to_write)

        # do the second half of _fields_sync the "normal" way
        for partner, vals in zip(partners, vals_list, strict=True):
            partner._children_sync(vals)
            partner._handle_first_contact_creation()
        return partners

    def create_company(self) -> bool:
        self.ensure_one()
        if new_company := self._create_contact_parent_company():
            # Set new company as my parent
            self.write(
                {
                    "parent_id": new_company.id,
                    "child_ids": [
                        Command.update(partner_id, {"parent_id": new_company.id})
                        for partner_id in self.child_ids.ids
                    ],
                }
            )
        return True

    def _create_contact_parent_company(self) -> Self:
        self.ensure_one()
        if self.company_name:
            # Create parent company
            values = {
                "name": self.company_name,
                "is_company": True,
                "vat": self.vat,
            }
            values.update(self._convert_fields_to_values(self._address_fields()))
            return self.create(values)
        return self.browse()

    def open_commercial_entity(self) -> dict[str, Any]:
        """Utility method used to add an "Open Company" button in partner views"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": self.commercial_partner_id.id,
            "target": "current",
        }

    @api.depends(
        "complete_name",
        "email",
        "vat",
        "state_id",
        "country_id",
        "commercial_company_name",
    )
    @api.depends_context(
        "show_address",
        "partner_show_db_id",
        "show_email",
        "show_vat",
        "lang",
        "formatted_display_name",
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
                if partner.parent_id or partner.company_name:
                    name = (
                        f"{partner.company_name or partner.parent_id.name} \t "
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
        """Override of orm's name_create method for partners. The purpose is
        to handle some basic formats to create partners using the
        name_create.
        If only an email address is received and that the regex cannot find
        a name, the name will have the email value.
        If 'force_email' key in context: must find the email address."""
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
        if email_normalized:  # keep default_email in context
            create_values["email"] = email_normalized
        partner = self.create(create_values)
        return partner.id, partner.display_name

    @api.model
    def find_or_create(self, email: str, assert_valid_email: bool = False) -> Self:
        """Find a partner with the given ``email`` or use :meth:`name_create`
        to create a new one.

        :param str email: email-like string, which should contain at least one email,
            e.g. ``"Raoul Grosbedon <r.g@grosbedon.fr>"``
        :param bool assert_valid_email: raise if no valid email is found
        :return: newly created record
        """
        if not email:
            raise ValueError(_("An email is required for find_or_create to work"))

        parsed_name, parsed_email_normalized = tools.parse_contact_from_email(email)
        if not parsed_email_normalized and assert_valid_email:
            raise ValueError(
                _("A valid email is required for find_or_create to work properly.")
            )

        if parsed_email_normalized:
            partners = self.search(
                [("email", "=ilike", parsed_email_normalized)], limit=1
            )
            if partners:
                return partners

        create_values = {self._rec_name: parsed_name or parsed_email_normalized}
        if parsed_email_normalized:  # keep default_email in context
            create_values["email"] = parsed_email_normalized
        return self.create(create_values)

    def address_get(self, adr_pref: list[str] | None = None) -> dict[str, int | bool]:
        """Find contacts/addresses of the right type(s) by doing a depth-first-search
        through descendants within company boundaries (stop at entities flagged ``is_company``)
        then continuing the search at the ancestors that are within the same company boundaries.
        Defaults to partners of type ``'default'`` when the exact type is not found, or to the
        provided partner itself if no type ``'default'`` is found either."""
        adr_pref = set(adr_pref or [])
        if "contact" not in adr_pref:
            adr_pref.add("contact")
        result = {}
        visited = set()
        for partner in self:
            current_partner = partner
            while current_partner:
                to_scan = deque([current_partner])
                # Scan descendants, DFS
                while to_scan:
                    record = to_scan.popleft()
                    visited.add(record)
                    if record.type in adr_pref and not result.get(record.type):
                        result[record.type] = record.id
                    if len(result) == len(adr_pref):
                        return result
                    # Prepend unvisited non-company children (DFS order)
                    children = [
                        c
                        for c in record.child_ids
                        if c not in visited
                        if not c.is_company
                    ]
                    if children:
                        to_scan.extendleft(reversed(children))

                # Continue scanning at ancestor if current_partner is not a commercial entity
                if current_partner.is_company or not current_partner.parent_id:
                    break
                current_partner = current_partner.parent_id

        # default to type 'contact' or the first partner itself
        default = result.get("contact", self[:1].id or False)
        for adr_type in adr_pref:
            result[adr_type] = result.get(adr_type) or default
        return result

    @api.model
    def view_header_get(self, view_id: int | None, view_type: str) -> str | bool:
        if self.env.context.get("category_id"):
            return _(
                "Partners: %(category)s",
                category=self.env["res.partner.category"]
                .browse(self.env.context["category_id"])
                .name,
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
        # get the information that will be injected into the display format
        # get the address format
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
        """
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param without_company: if address contains company
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: str
        """
        address_format, args = self._prepare_display_address(without_company)
        try:
            return address_format % args
        except KeyError, ValueError:
            # address_format is user-editable in res.country; fall back gracefully
            # if it references a placeholder that doesn't exist in args.
            return " ".join(filter(None, args.values()))

    def _display_address_depends(self) -> list[str]:
        # field dependencies of method _display_address()
        return self._formatting_address_fields() + [
            "country_id",
            "company_name",
            "state_id",
        ]

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
        """Validate that state_id/country_id pairs are consistent on import.

        During import, field values are resolved independently by name search, so
        a state from one country may be paired with a different country.  This
        method corrects such mismatches: if a state does not belong to the
        specified country, it searches for a state with the same code in the
        correct country, or clears state_id when none exists.
        """
        States = self.env["res.country.state"]
        states_ids = {vals["state_id"] for vals in vals_list if vals.get("state_id")}
        # Fetch country_id AND code in one query so we need no additional browse calls.
        state_info_by_id = {
            rec["id"]: rec
            for rec in States.search_read(
                [("id", "in", list(states_ids))], ["country_id", "code"]
            )
        }
        for vals in vals_list:
            if not vals.get("state_id") or not vals.get("country_id"):
                continue
            state_info = state_info_by_id.get(vals["state_id"])
            if state_info is None:
                # State was deleted or inaccessible between prefetch and lookup; skip.
                continue
            state_country_id = state_info["country_id"][0]
            if state_country_id != vals["country_id"]:
                # State belongs to a different country than the one given — try to
                # find a state with the same code in the correct country.
                state_domain = [
                    ("code", "=", state_info["code"]),
                    ("country_id", "=", vals["country_id"]),
                ]
                matching_state = States.search(state_domain, limit=1)
                vals["state_id"] = matching_state.id  # 0/False if not found

    def _get_country_name(self) -> str:
        return self.country_id.name or ""

    def _get_all_addr(self) -> list[ValuesType]:
        self.ensure_one()
        return [
            {
                "contact_type": self.type,
                "street": self.street,
                "zip": self.zip,
                "city": self.city,
                "country": self.country_id.code,
            }
        ]
