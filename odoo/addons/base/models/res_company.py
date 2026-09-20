import base64
import functools
from typing import Any, Self

from odoo import _lt, api, fields, models, modules, tools
from odoo.api import SUPERUSER_ID, ValuesType
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import file_open, ormcache
from odoo.tools.image import image_process

_debug = DebugLog(__name__)


@functools.cache
def _get_default_logo():
    with file_open("base/static/img/res_company_logo.png", "rb") as file:
        return base64.b64encode(file.read())


class ResCompany(models.Model):
    _name = "res.company"
    _description = "Companies"
    _inherit = [
        "mixin.format.address",
        "mixin.format.vat.label",
        "mixin.hierarchy",
    ]
    _inherits = {"res.partner": "partner_id"}
    _order = "sequence, name"
    _rec_names_search = ["code", "name"]
    # display_name is `code or name`; _search_display_name only narrows the
    # default composition under `user_preference`
    _display_name_column = ("code", "name")
    _display_name_context_keys = ("user_preference",)
    _display_name_search_default = True
    # a tenant's row is governed by the tenant's rules, and its identity is
    # readable by whoever may read the tenant; the party's rules govern the
    # party's other fields
    _inherits_rules = False
    _inherits_sudo_fields = (
        "name",
        "email",
        "phone_ids",
        "website",
        "vat",
        "company_registry",
        "company_registry_placeholder",
        "bank_ids",
        "street",
        "street2",
        "zip",
        "city",
        "state_id",
        "country_id",
        "country_code",
        "image_1920",
        "image_1024",
        "image_512",
        "image_256",
        "image_128",
        "avatar_1920",
        "avatar_1024",
        "avatar_512",
        "avatar_256",
        "avatar_128",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Party",
        index=True,
        required=True,
        ondelete="restrict",
    )
    code = fields.Char(
        string="Short Code",
        size=6,
        help="Short, untranslated handle for the company, shown wherever the "
        "company is referenced instead of its full legal name. Companies "
        "without one are referenced by name.",
    )
    complete_name = fields.Char(
        compute="_compute_complete_name",
        store=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        default=10,
        help="Used to order Companies in the company switcher",
    )

    parent_id = fields.Many2one(
        comodel_name="res.company",
        string="Parent Company",
        index=True,
        ondelete="restrict",
    )
    child_ids = fields.One2many(
        comodel_name="res.company",
        inverse_name="parent_id",
        string="Branches",
    )
    all_child_ids = fields.One2many(
        comodel_name="res.company",
        inverse_name="parent_id",
        context={"active_test": False},
    )
    parent_ids = fields.Many2many(
        comodel_name="res.company",
        compute="_compute_hierarchy",
        compute_sudo=True,
    )
    root_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_hierarchy",
        search="_search_root_id",
        compute_sudo=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self._default_currency_id(),
        required=True,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="res_company_users_rel",
        column1="cid",
        column2="user_id",
        string="Accepted Users",
    )
    logo_web = fields.Binary(
        attachment=False,
        compute="_compute_logo_web",
        store=True,
    )
    uses_default_logo = fields.Boolean(
        compute="_compute_uses_default_logo",
        store=True,
    )
    report_config_id = fields.Many2one(
        comodel_name="report.config",
        compute="_compute_report_config_id",
    )
    uninstalled_l10n_module_ids = fields.Many2many(
        comodel_name="ir.module.module",
        compute="_compute_uninstalled_l10n_module_ids",
    )

    _code_uniq = models.Constraint(
        "unique (code)",
        "The company short code must be unique!",
    )

    _hierarchy_cycle_message = _lt("You cannot create recursive companies.")

    @api.constrains("active")
    def _check_active(self) -> None:
        inactive_companies = self.filtered(lambda c: not c.active)
        if not inactive_companies:
            return
        _debug.logic("archive_checked", companies=inactive_companies.ids)
        offenders = self.env["res.users"]._read_group(
            [
                ("company_id", "in", inactive_companies.ids),
                ("active", "=", True),
            ],
            groupby=["company_id"],
            aggregates=["__count"],
        )
        if offenders:
            _debug.logic(
                "archive_refused",
                companies=inactive_companies.ids,
                offenders=len(offenders),
            )
            raise ValidationError(
                self.env._(
                    "The following companies cannot be archived because they are still "
                    "used as the default company of active users:\n%(details)s",
                    details="\n".join(
                        self.env._(
                            "- %(company_name)s (%(active_users)s users)",
                            company_name=company.name,
                            active_users=count,
                        )
                        for company, count in offenders
                    ),
                )
            )

    @api.constrains("partner_id")
    def _check_party_name_unique(self) -> None:
        names = self.mapped("name")
        twins = (
            self.sudo()
            .with_context(active_test=False)
            .search_count([("name", "in", names), ("id", "not in", self.ids)])
        )
        if twins or len(names) != len(set(names)):
            _debug.logic("company_name_duplicate", companies=self.ids)
            raise ValidationError(self.env._("The company name must be unique!"))

    @api.constrains(
        lambda self: self._get_field_names_delegated_to_root() + ["parent_id"]
    )
    def _check_delegated_fields_match_root(self) -> None:
        for company in self:
            if company.parent_id:
                for fname in company._get_field_names_delegated_to_root():
                    if company[fname] != company.parent_id[fname]:
                        _debug.logic(
                            "delegated_field_mismatch", company=company.id, field=fname
                        )
                        description = (
                            self.env["ir.model.fields"]
                            ._get("res.company", fname)
                            .field_description
                        )
                        raise ValidationError(
                            self.env._(
                                "The %s of a subsidiary must be the same as its root company.",
                                description,
                            )
                        )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        context_parent_id = self.env.context.get("default_parent_id")
        self = self.with_context(
            {k: v for k, v in self.env.context.items() if k != "default_parent_id"}
        )
        vals_list = [dict(self._normalize_vals(vals)) for vals in vals_list]
        default_logo = self._default_logo()
        for vals in vals_list:
            if context_parent_id and "parent_id" not in vals:
                vals["parent_id"] = context_parent_id
            if not vals.get("partner_id"):
                vals.setdefault("is_company", True)
                vals.setdefault("image_1920", default_logo)

        for vals in vals_list:
            if parent := self.browse(vals.get("parent_id")):
                for fname in self._get_field_names_delegated_to_root():
                    vals.setdefault(
                        fname,
                        self._fields[fname].convert_to_write(parent[fname], parent),
                    )
                _debug.logic(
                    "delegated_fields_inherited",
                    parent=parent.id,
                    fields=len(self._get_field_names_delegated_to_root()),
                )

        self.env.registry.clear_cache()
        _debug.lifecycle("registry_cache_cleared", by="create")
        config_vals_list = [self._split_config_vals(vals) for vals in vals_list]
        companies = super().create(vals_list)
        self.env.registry.clear_cache()
        for field in self._config_link_fields().values():
            self.env[field.comodel_name]._for_each(companies)
        _debug.lifecycle(
            "create",
            count=len(companies),
            branches=sum(1 for vals in vals_list if vals.get("parent_id")),
        )

        if companies:
            (self.env.user | self.env["res.users"].browse(SUPERUSER_ID)).write(
                {
                    "company_ids": [Command.link(company.id) for company in companies],
                }
            )
        # the creating user is a member of the new company before its
        # configuration is written: what the write triggers may work in it
        for company, config_vals in zip(companies, config_vals_list, strict=True):
            for link, vals in config_vals.items():
                company[link].write(vals)

        inactive_currencies = companies.currency_id.sudo().filtered(
            lambda c: not c.active
        )
        if inactive_currencies:
            _debug.lifecycle("currencies_activated", currencies=inactive_currencies.ids)
            inactive_currencies.active = True

        companies_needs_l10n = companies.filtered("country_id")
        _debug.pipeline(
            "create_l10n",
            companies=len(companies),
            with_country=len(companies_needs_l10n),
        )
        if companies_needs_l10n:
            companies_needs_l10n.install_l10n_modules()

        return companies

    def write(self, vals: dict[str, Any]) -> bool:
        vals = self._normalize_vals(vals)
        for link, link_vals in self._split_config_vals(vals).items():
            self[link].write(link_vals)
        if "parent_id" in vals and any(
            c.parent_id.id != vals["parent_id"] for c in self
        ):
            _debug.logic("write_refused", companies=self.ids, reason="parent_change")
            raise UserError(self.env._("The company hierarchy cannot be changed."))

        if vals.get("currency_id"):
            currency = self.env["res.currency"].browse(vals["currency_id"])
            if not currency.active:
                _debug.lifecycle("currencies_activated", currencies=currency.ids)
                currency.write({"active": True})

        companies_needs_l10n = (
            vals.get("country_id")
            and self.filtered(lambda company: not company.country_id)
        ) or self.browse()

        _debug.lifecycle("write", count=len(self), fields=list(vals))
        res = super().write(vals)
        invalidation_fields = self._get_cache_invalidation_fields()
        if not invalidation_fields.isdisjoint(vals):
            _debug.lifecycle(
                "registry_cache_cleared",
                by="write",
                fields=sorted(invalidation_fields & set(vals)),
            )
            self.env.registry.clear_cache()

        if vals.get("active") is False:
            _debug.lifecycle(
                "branches_archived", companies=self.ids, branches=len(self.child_ids)
            )
            self.child_ids.active = False

        delegated_changed = set(vals) & set(self._get_field_names_delegated_to_root())
        if delegated_changed:
            roots = self.filtered(lambda company: not company.parent_id)
            all_branches = self.sudo().search(
                [("id", "child_of", roots.ids), ("id", "not in", roots.ids)]
            )
            _debug.logic(
                "delegated_fields_propagated",
                fields=sorted(delegated_changed),
                roots=len(roots),
                branches=len(all_branches),
            )
            for company in roots:
                branches = all_branches.filtered(
                    lambda branch, root=company: root in branch.parent_ids
                )
                changed_vals = {
                    fname: self._fields[fname].convert_to_write(
                        company[fname], branches
                    )
                    for fname in sorted(delegated_changed)
                }
                branches.write(changed_vals)

        if companies_needs_l10n:
            _debug.pipeline("write_l10n", companies=companies_needs_l10n.ids)
            companies_needs_l10n.install_l10n_modules()

        return res

    def copy(self, default: ValuesType | None = None) -> Self:
        _debug.logic("copy_refused", companies=self.ids)
        raise UserError(
            self.env._(
                "Duplicating a company is not allowed. Please create a new company instead."
            )
        )

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", count=len(self))
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    def _default_logo(self) -> bytes:
        return _get_default_logo()

    def _default_currency_id(self) -> models.Model:
        return self.env.user.company_id.currency_id

    @api.depends("parent_path")
    def _compute_hierarchy(self) -> None:
        for company in self.with_context(active_test=False):
            company.parent_ids = (
                self.browse(company._get_ancestor_ids(include_self=True)) or company
            )
            company.root_id = company.parent_ids[0]
        _debug.perf.count("hierarchy_computed", companies=len(self))

    @api.depends("image_1920")
    def _compute_logo_web(self) -> None:
        with _debug.perf("logo_web_computed", companies=len(self)) as span:
            resized = 0  # debuglog
            for company in self:
                img = company.image_1920
                resized += bool(img)  # debuglog
                company.logo_web = img and base64.b64encode(
                    image_process(base64.b64decode(img), size=(180, 0))
                )
            span.set(resized=resized)

    @api.depends("image_1920")
    def _compute_uses_default_logo(self) -> None:
        default_logo = _get_default_logo()
        for company in self:
            company.uses_default_logo = (
                not company.image_1920 or company.image_1920 == default_logo
            )

    @api.depends("country_id")
    def _compute_uninstalled_l10n_module_ids(self) -> None:
        _debug.pipeline(
            "uninstalled_l10n_modules_lookup",
            companies=len(self),
            countries=len(self.country_id),
        )
        self.env["ir.module.module"].flush_model(
            ["auto_install", "country_ids", "dependencies_id"]
        )
        self.env["ir.module.module.dependency"].flush_model()
        self.env.cr.execute(
            """
            SELECT
                country.id,
                ARRAY_AGG(module.id)
            FROM
                ir_module_module module,
                res_country country
            WHERE module.auto_install
                AND state != ALL(%(install_states)s)
                AND NOT EXISTS (
                    SELECT 1
                    FROM ir_module_module_dependency d
                    JOIN ir_module_module mdep ON (d.name = mdep.name)
                    WHERE d.module_id = module.id
                        AND d.auto_install_required
                        AND mdep.state != ALL(%(install_states)s)
                )
                AND EXISTS (
                    SELECT 1
                    FROM module_country mc
                    WHERE mc.module_id = module.id
                        AND mc.country_id = country.id
                )
               AND country.id = ANY(%(country_ids)s)
            GROUP BY country.id
            """,
            {
                "country_ids": self.country_id.ids,
                "install_states": ["installed", "to install", "to upgrade"],
            },
        )
        mapping = dict(self.env.cr.fetchall())
        _debug.perf.count(
            "uninstalled_l10n_modules_computed",
            companies=len(self),
            countries=len(mapping),
            modules=sum(len(ids) for ids in mapping.values()),
        )
        for company in self:
            company.uninstalled_l10n_module_ids = self.env["ir.module.module"].browse(
                mapping.get(company.country_id.id)
            )

    @api.depends("code", "name")
    def _compute_complete_name(self) -> None:
        for company in self:
            company.complete_name = " - ".join(
                part for part in (company.code, company.name) if part
            )

    @api.depends("code", "name")
    def _compute_display_name(self) -> None:
        for company in self:
            company.display_name = company.code or company.name

    def _compute_report_config_id(self) -> None:
        configs = self.env["report.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.report_config_id = by_company.get(company.id)

    @api.onchange("country_id")
    def _onchange_country_id(self) -> None:
        if self.country_id:
            self.currency_id = self.country_id.currency_id

    @api.onchange("parent_id")
    def _onchange_parent_id(self) -> None:
        if self.parent_id:
            synced = 0  # debuglog
            for fname in self._get_field_names_delegated_to_root():
                if self[fname] != self.parent_id[fname]:
                    self[fname] = self.parent_id[fname]
                    synced += 1  # debuglog
            _debug.logic(
                "onchange_parent_delegated", parent=self.parent_id.id, synced=synced
            )

    def action_all_company_branches(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Branches"),
            "res_model": "res.company",
            "domain": [("parent_id", "=", self.id)],
            "context": {
                "active_test": False,
                "default_parent_id": self.id,
            },
            "views": [[False, "list"], [False, "kanban"], [False, "form"]],
        }

    @api.model
    def _config_link_fields(self) -> dict[str, fields.Field]:
        return {
            name: field
            for name, field in self._fields.items()
            if name.endswith("_config_id")
            and field.is_many2one
            and getattr(self.env[field.comodel_name], "_company_config", False)
        }

    def _get_cache_invalidation_fields(self) -> set[str]:
        return {
            "active",
            "sequence",
            "partner_id",
            "user_ids",
        }

    @ormcache("tuple(self.env.companies.ids)", "self.id", "self.env.uid")
    def __get_accessible_branch_ids(self) -> list[int]:
        self.check_singleton()

        accessible_branch_ids = []
        accessible = self.env.companies
        current = self.sudo()
        seen = set()
        while current:
            new = current - current.browse(seen)
            if not new:
                break
            accessible_branch_ids.extend((new & accessible).ids)
            seen.update(new.ids)
            current = new.child_ids

        _debug.logic(
            "accessible_branches",
            company=self.id,
            walked=len(seen),
            accessible=len(accessible_branch_ids),
            superuser_fallback=not accessible_branch_ids
            and self.env.uid == SUPERUSER_ID,
        )
        if not accessible_branch_ids and self.env.uid == SUPERUSER_ID:
            return self.ids

        return accessible_branch_ids

    def _get_accessible_branches(self) -> Self:
        return self.browse(self.__get_accessible_branch_ids())

    def _get_field_names_delegated_to_root(self) -> list[str]:
        return ["currency_id"]

    @ormcache()
    def _get_company_partner_ids(self):
        partner_ids = tuple(
            self.env["res.company"]
            .sudo()
            .with_context(active_test=False)
            .search([])
            .partner_id.ids
        )
        _debug.perf.count("company_partner_ids_computed", partners=len(partner_ids))
        return partner_ids

    @api.model
    def _get_main_company(self) -> Self:
        try:
            main_company = self.sudo().env.ref("base.main_company")
        except ValueError:
            main_company = (
                self.env["res.company"].sudo().search([], limit=1, order="id")
            )
            _debug.logic("main_company_fallback", company=main_company.id)

        return main_company

    def _get_public_user(self) -> models.Model:
        self.check_singleton()
        login = f"public-user@company-{self.id}.com"
        existing = (
            self.env["res.users"]
            .sudo()
            .with_context(active_test=False)
            .search([("login", "=", login), ("company_id", "=", self.id)], limit=1)
        )
        if existing:
            return existing
        _debug.lifecycle("public_user_created", company=self.id, login=login)
        return (
            self.env.ref("base.public_user")
            .sudo()
            .copy(
                {
                    "name": f"Public user for {self.name}",
                    "login": login,
                    "company_id": self.id,
                    "company_ids": [Command.set([self.id])],
                }
            )
        )

    @api.model
    def _get_view(
        self,
        view_id: int | None = None,
        view_type: str = "form",
        **options: Any,
    ) -> tuple:
        delegated_fnames = set(self._get_field_names_delegated_to_root())
        arch, view = super()._get_view(view_id, view_type, **options)
        marked = 0  # debuglog
        for f in arch.iter("field"):
            if f.get("name") in delegated_fnames:
                f.set("readonly", "parent_id != False")
                marked += 1  # debuglog
        _debug.logic("delegated_fields_readonly", view_type=view_type, fields=marked)
        return arch, view

    def install_l10n_modules(self) -> Any:
        uninstalled_modules = self.uninstalled_l10n_module_ids
        is_ready_and_not_test = (
            not tools.config["test_enable"]
            and self.env.registry.ready
            and not modules.module.current_test
            and not self.env.context.get("install_mode")
            and not self.env.context.get("import_file")
        )
        _debug.logic(
            "install_l10n_modules",
            companies=self.ids,
            modules=uninstalled_modules.mapped("name"),
            ready=is_ready_and_not_test,
        )
        if uninstalled_modules and is_ready_and_not_test:
            with _debug.perf(
                "l10n_modules_installed",
                cr=self.env.cr,
                modules=len(uninstalled_modules),
            ):
                return uninstalled_modules.button_immediate_install()
        return is_ready_and_not_test

    def _normalize_vals(self, vals: dict[str, Any]) -> dict[str, Any]:
        if "code" not in vals:
            return vals
        code = (vals["code"] or "").strip().upper()
        _debug.logic("code_sanitized", code=code or False, changed=code != vals["code"])
        return {**vals, "code": code or False}

    @api.model
    def _search_display_name(self, operator: str, value: str) -> Domain:
        context = dict(self.env.context)
        newself = self
        constraint = Domain.TRUE
        if context.pop("user_preference", None):
            companies = self.env.user.company_ids
            constraint = Domain("id", "in", companies.ids)
            newself = newself.sudo()
            _debug.logic(
                "display_name_search_user_preference",
                uid=self.env.uid,
                companies=len(companies),
                operator=operator,
            )
        newself = newself.with_context(context)
        domain = super(ResCompany, newself)._search_display_name(operator, value)
        return domain & constraint

    def _search_root_id(self, operator: str, value: Any) -> Domain:
        if operator not in ("in", "not in"):
            return NotImplemented
        roots = (
            self.sudo()
            .with_context(active_test=False)
            .browse(value)
            .filtered(lambda company: not company.parent_id)
        )
        domain = Domain("id", "child_of", roots.ids) if roots else Domain.FALSE
        return ~domain if operator == "not in" else domain

    @api.model
    def _search_config_link(
        self, comodel_name: str, operator: str, value: Any
    ) -> list[tuple[str, str, Any]]:
        Config = self.env[comodel_name].sudo()
        if operator in ("any", "not any"):
            # a path through the link: the configuration's own domain
            configs = Config.search(value)
            _debug.logic(
                "config_link_searched",
                config=comodel_name,
                operator=operator,
                companies=configs.company_id.ids,
            )
            return [
                (
                    "id",
                    "not in" if operator == "not any" else "in",
                    configs.company_id.ids,
                )
            ]
        configs = Config.search([("id", operator, value)])
        _debug.logic(
            "config_link_searched",
            config=comodel_name,
            operator=operator,
            companies=configs.company_id.ids,
        )
        return [("id", "in", configs.company_id.ids)]

    def _split_config_vals(self, vals: dict[str, Any]) -> dict[str, dict[str, Any]]:
        config_vals: dict[str, dict[str, Any]] = {}
        for link, field in self._config_link_fields().items():
            config_fields = self.env[field.comodel_name]._fields
            keys = [
                key
                for key in vals
                if key not in self._fields
                and key in config_fields
                and key != "company_id"
            ]
            if keys:
                config_vals[link] = {key: vals.pop(key) for key in keys}
                _debug.logic("config_vals_routed", link=link, fields=keys)
        return config_vals

    def _is_every_branch_selected(self) -> bool:
        every = self == self.sudo().search([("id", "child_of", self.root_id.ids)])
        _debug.logic(
            "every_branch_selected",
            companies=len(self),
            roots=len(self.root_id),
            result=every,
        )
        return every
