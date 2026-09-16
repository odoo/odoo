import base64
import contextlib
import functools
import logging
import platform
from collections import defaultdict
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, NamedTuple, Self

import lxml.html
import psycopg
from markupsafe import Markup

from odoo import _, api, fields, models, modules, tools
from odoo.api import ValuesType
from odoo.db.schema import column_exists
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.parse_version import parse_version
from odoo.libs.rst import render_html as render_rst_html
from odoo.modules.module import (
    Manifest,
    MissingDependencyError,
    get_module_content_checksum,
)
from odoo.tools import SQL, config
from odoo.tools.misc import get_flag, topological_sort
from odoo.tools.translate import (
    TranslationImporter,
    code_translations,
    get_datafile_translation_path,
    get_po_paths,
)

from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterator

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

ACTION_DICT = {
    "view_mode": "form",
    "res_model": "base.module.upgrade",
    "target": "new",
    "type": "ir.actions.act_window",
}


def _modules_whose_records_it_writes(data_file_checksums: object) -> set[str] | None:
    if not isinstance(data_file_checksums, dict):
        return None
    files = data_file_checksums.get("files")
    if not isinstance(files, dict):
        return None
    modules: set[str] = set()
    for entry in files.values():
        xmlids = entry.get("xmlids") if isinstance(entry, dict) else None
        for xmlid in xmlids or ():
            module, dot, _name = xmlid.partition(".")
            if dot:
                modules.add(module)
    return modules


class UpdateListResult(NamedTuple):
    updated: int
    added: int


def localize_description_images(module_name: str, doc: str) -> str:
    html = lxml.html.document_fromstring(doc)
    for element, _attribute, _link, _pos in html.iterlinks():
        src = element.get("src")
        if src and "//" not in src and "static/" not in src:
            element.set("src", f"/{module_name}/static/description/{src}")
    return tools.html_sanitize(lxml.html.tostring(html, encoding="unicode"))


class LazyModuleNames:
    __slots__ = ("records",)

    def __init__(self, records: Any) -> None:
        self.records = records

    def __str__(self) -> str:
        return str(self.records.sudo().mapped("display_name"))


def assert_log_admin_access[T](method: T, /) -> T:

    @functools.wraps(method)
    def check_and_log(self, *args: Any, **kwargs: Any) -> Any:
        user = self.env.user
        origin = request.httprequest.remote_addr if request else "n/a"
        allowed = self.env.is_admin()
        log = _logger.info if allowed else _logger.warning
        log(
            "%s access to module.%s on %s to user %s #%s via %s",
            "ALLOW" if allowed else "DENY",
            method.__name__,
            LazyModuleNames(self),
            user.login,
            user.id,
            origin,
        )
        if not allowed:
            _debug.logic("admin_access.denied", method=method.__name__, uid=user.id)
            raise AccessDenied
        return method(self, *args, **kwargs)

    return check_and_log


GROUP_HIERARCHY_FIELDS = frozenset(("name", "privilege_ids"))


class IrModuleCategory(models.Model):
    _name = "ir.module.category"
    _description = "Application"
    _order = "sequence, name, id"
    _allow_sudo_commands = False

    name = fields.Char(
        translate=True,
        required=True,
    )
    parent_id = fields.Many2one(
        comodel_name="ir.module.category",
        string="Parent Application",
        index=True,
    )
    child_ids = fields.One2many(
        comodel_name="ir.module.category",
        inverse_name="parent_id",
        string="Child Applications",
    )
    module_ids = fields.One2many(
        comodel_name="ir.module.module",
        inverse_name="category_id",
        string="Modules",
    )
    privilege_ids = fields.One2many(
        comodel_name="res.groups.privilege",
        inverse_name="category_id",
        string="Privileges",
    )
    description = fields.Text(translate=True)
    sequence = fields.Integer()
    visible = fields.Boolean(default=True)
    exclusive = fields.Boolean()
    xml_id = fields.Char(
        string="External ID",
        compute="_compute_xml_id",
    )

    def _compute_xml_id(self) -> None:
        xml_ids = defaultdict(list)
        domain = [("model", "=", self._name), ("res_id", "in", self.ids)]
        for data in (
            self.env["ir.model.data"]
            .sudo()
            .search_read(domain, ["module", "name", "res_id"])
        ):
            xml_ids[data["res_id"]].append(f"{data['module']}.{data['name']}")
        for cat in self:
            cat.xml_id = xml_ids.get(cat.id, [""])[0]

    @api.constrains("parent_id")
    def _check_parent_not_circular(self) -> None:
        if self._has_cycle():
            _debug.logic("category.cycle_rejected", categories=self.ids)
            raise ValidationError(_("Error ! You cannot create recursive categories."))

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        records = super().create(vals_list)
        self.env.registry.clear_cache("groups")
        _debug.lifecycle("category.create", count=len(records))
        return records

    def write(self, vals: dict[str, Any]) -> bool:
        res = super().write(vals)
        if not GROUP_HIERARCHY_FIELDS.isdisjoint(vals):
            self.env.registry.clear_cache("groups")
        _debug.lifecycle(
            "category.write",
            count=len(self),
            fields=list(vals),
            groups_cache_cleared=not GROUP_HIERARCHY_FIELDS.isdisjoint(vals),
        )
        return res

    def unlink(self) -> bool:
        res = super().unlink()
        self.env.registry.clear_cache("groups")
        _debug.lifecycle("category.unlink", count=len(self))
        return res


STATES = [
    ("uninstallable", "Uninstallable"),
    ("uninstalled", "Not Installed"),
    ("installed", "Installed"),
    ("to upgrade", "To be upgraded"),
    ("to remove", "To be removed"),
    ("to install", "To be installed"),
]

AUTO_INSTALL_TRIGGER_STATES = frozenset(("installed", "to install", "to upgrade"))

PENDING_STATES = ("to install", "to upgrade", "to remove")

STUDIO_CUSTOMIZATION = "studio_customization"

STABLE_CACHE_FIELDS = frozenset(("name", "state"))

UNSATISFIABLE_DEPENDENCY_STATES = frozenset(("uninstallable", "unknown"))

LINK_STATES = [*STATES, ("unknown", "Unknown")]


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _is_registry_metadata = True
    _rec_name = "shortdesc"
    _rec_names_search = ["name", "shortdesc", "summary"]
    _description = "Module"
    _order = "application desc,sequence,name"
    _allow_sudo_commands = False

    name = fields.Char(
        string="Technical Name",
        readonly=True,
        required=True,
    )
    category_id = fields.Many2one(
        comodel_name="ir.module.category",
        index=True,
        readonly=True,
    )
    shortdesc = fields.Char(
        string="Module Name",
        translate=True,
        readonly=True,
    )
    summary = fields.Char(
        translate=True,
        readonly=True,
    )
    description = fields.Text(
        translate=True,
        readonly=True,
    )
    description_html = fields.Html(
        string="Description HTML",
        compute="_compute_description_html",
    )
    author = fields.Char(readonly=True)
    maintainer = fields.Char(readonly=True)
    contributors = fields.Text(readonly=True)
    website = fields.Char(readonly=True)

    manifest_version = fields.Char(compute="_compute_manifest_version")
    db_version = fields.Char(
        string="Installed Version",
        readonly=True,
    )

    url = fields.Char(
        string="URL",
        readonly=True,
    )
    sequence = fields.Integer(default=100)
    dependencies_id = fields.One2many(
        comodel_name="ir.module.module.dependency",
        inverse_name="module_id",
        readonly=True,
    )
    country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="module_country",
        column1="module_id",
        column2="country_id",
    )
    exclusion_ids = fields.One2many(
        comodel_name="ir.module.module.exclusion",
        inverse_name="module_id",
        string="Exclusions",
        readonly=True,
    )
    auto_install = fields.Boolean(
        string="Automatic Installation",
        help="An auto-installable module is installed by the system as soon as "
        "the dependencies it names as triggers are being installed, provided "
        "every one of its dependencies can be satisfied.",
    )
    state = fields.Selection(
        selection=STATES,
        string="Status",
        default="uninstallable",
        index=True,
        readonly=True,
    )
    demo = fields.Boolean(
        string="Demo Data",
        default=False,
        readonly=True,
    )
    license = fields.Selection(
        selection=[
            ("GPL-2", "GPL Version 2"),
            ("GPL-2 or any later version", "GPL-2 or later version"),
            ("GPL-3", "GPL Version 3"),
            ("GPL-3 or any later version", "GPL-3 or later version"),
            ("AGPL-3", "Affero GPL-3"),
            ("LGPL-3", "LGPL Version 3"),
            ("Other OSI approved licence", "Other OSI Approved License"),
            ("OEEL-1", "Odoo Enterprise Edition License v1.0"),
            ("OPL-1", "Odoo Proprietary License v1.0"),
            ("Other proprietary", "Other Proprietary"),
        ],
        default="LGPL-3",
        readonly=True,
    )
    menus_by_module = fields.Text(
        string="Menus",
        compute="_compute_records_by_module",
    )
    reports_by_module = fields.Text(
        string="Reports",
        compute="_compute_records_by_module",
    )
    views_by_module = fields.Text(
        string="Views",
        compute="_compute_records_by_module",
    )
    application = fields.Boolean(readonly=True)
    icon = fields.Char(string="Icon URL")
    icon_image = fields.Binary(
        string="Icon",
        compute="_compute_icon_display",
    )
    icon_flag = fields.Char(
        string="Flag",
        compute="_compute_icon_display",
    )
    to_buy = fields.Boolean(
        string="Odoo Enterprise Module",
        default=False,
    )
    has_iap = fields.Boolean(compute="_compute_has_iap")
    data_file_checksums = fields.Json(
        readonly=True,
        prefetch=False,
    )
    content_checksum = fields.Char(
        readonly=True,
        prefetch=False,
    )

    _name_uniq = models.Constraint(
        "UNIQUE (name)",
        "The name of the module must be unique!",
    )

    @classmethod
    def _is_installable(cls, name: str) -> bool:
        manifest = cls.get_module_info(name)
        return manifest["installable"] if manifest else True

    @classmethod
    def get_module_info(cls, name: str) -> Manifest | None:
        if not name:
            return None
        return modules.Manifest.for_addon(name, display_warning=False)

    def _read_description_index_html(self) -> str:
        self.check_singleton()
        path = str(Path(self.name, "static/description/index.html"))
        try:
            with tools.file_open(path, "rb", filter_ext=(".html",)) as desc_file:
                return desc_file.read().decode(errors="replace").strip()
        except FileNotFoundError:
            _debug.logic("description.index_html_missing", module=self.name)
            return ""

    def _render_description_rst(self) -> str:
        self.check_singleton()
        raw_description = self.description or ""
        try:
            html, messages = render_rst_html(raw_description)
        except Exception as e:
            _debug.logic("description.rst_unrenderable", module=self.name)
            _logger.warning(
                "module %s: description is not renderable (%s), showing it raw",
                self.name,
                e,
            )
            return Markup("<pre><code>%s</code></pre>") % raw_description
        if messages:
            _logger.warning("module %s: description markup: %s", self.name, messages)
        return html

    @api.depends("name", "description")
    def _compute_description_html(self) -> None:
        with _debug.perf("description.compute", count=len(self)):
            for module in self:
                if not module.name:
                    module.description_html = False
                    continue
                doc = module._read_description_index_html() or (
                    module._render_description_rst()
                )
                module.description_html = localize_description_images(module.name, doc)

    @api.depends("name")
    def _compute_manifest_version(self) -> None:
        default_version = modules.adapt_version("1.0")
        for module in self:
            manifest = self.get_module_info(module.name)
            if _debug.logic.enabled and not manifest:
                _debug.logic("manifest.missing", module=module.name)
            module.manifest_version = (
                manifest["version"] if manifest else default_version
            )

    @api.depends("name", "state")
    def _compute_records_by_module(self) -> None:
        IrModelData = self.env["ir.model.data"].with_context(active_test=True)
        dmodels = ["ir.ui.view", "ir.actions.report", "ir.ui.menu"]

        active_mods = self.filtered(
            lambda m: m.state in ("installed", "to upgrade", "to remove")
        )
        for module in self - active_mods:
            module.views_by_module = ""
            module.reports_by_module = ""
            module.menus_by_module = ""
        if not active_mods:
            return

        imd_per_module: defaultdict[str, defaultdict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        imd_domain = [
            ("module", "in", [m.name for m in active_mods]),
            ("model", "in", dmodels),
        ]
        for data in IrModelData.sudo().search(imd_domain):
            imd_per_module[data.module][data.model].append(data.res_id)

        def existing(model):
            ids = [
                res_id
                for per_model in imd_per_module.values()
                for res_id in per_model[model]
            ]
            return self.env[model].browse(ids).exists()

        def format_view(v):
            prefix = "* INHERIT " if v.inherit_id else ""
            return f"{prefix}{v.name} ({v.type})"

        views = {v.id: format_view(v) for v in existing("ir.ui.view")}
        reports = {r.id: r.name for r in existing("ir.actions.report")}
        menus = {m.id: m.complete_name for m in existing("ir.ui.menu")}
        _debug.perf.count(
            "records_by_module.collected",
            modules=len(active_mods),
            views=len(views),
            reports=len(reports),
            menus=len(menus),
        )

        for module in active_mods:
            imd_models = imd_per_module[module.name]
            module.views_by_module = "\n".join(
                sorted(views[i] for i in imd_models["ir.ui.view"] if i in views)
            )
            module.reports_by_module = "\n".join(
                sorted(
                    reports[i] for i in imd_models["ir.actions.report"] if i in reports
                )
            )
            module.menus_by_module = "\n".join(
                sorted(menus[i] for i in imd_models["ir.ui.menu"] if i in menus)
            )

    @api.depends("icon")
    def _compute_icon_display(self) -> None:
        self.icon_image = ""
        self.icon_flag = ""
        for module in self:
            if not module.id:
                continue
            manifest = self.get_module_info(module.name)
            if module.icon:
                path = module.icon
            elif manifest:
                path = manifest.icon
            else:
                _debug.logic("icon.fallback_base", module=module.name)
                path = Manifest.for_addon("base").icon
            path = path.removeprefix("/")
            if path:
                try:
                    with tools.file_open(
                        path,
                        "rb",
                        filter_ext=(".png", ".svg", ".gif", ".jpeg", ".jpg"),
                    ) as image_file:
                        module.icon_image = base64.b64encode(image_file.read())
                except OSError, ValueError:
                    _debug.logic("icon.unreadable", module=module.name, path=path)
                    module.icon_image = ""
            countries = manifest["countries"] if manifest else []
            if len(countries) == 1:
                with contextlib.suppress(ValueError):
                    module.icon_flag = get_flag(countries[0].upper())

    @api.depends("name", "dependencies_id.name")
    def _compute_has_iap(self) -> None:
        iap = self.browse(self._get_id("iap") or [])
        iap_ids = set((iap | iap.downstream_dependencies(exclude_states=()))._ids)
        _debug.perf.count("has_iap.closure", iap_modules=len(iap_ids))
        for module in self:
            module.has_iap = bool(module.id) and module.id in iap_ids

    @api.ondelete(at_uninstall=False)
    def _unlink_except_installed(self) -> None:
        for module in self:
            if module.state in (
                "installed",
                "to upgrade",
                "to remove",
                "to install",
            ):
                _debug.logic(
                    "unlink.rejected",
                    module=module.name,
                    state=module.state,
                    reason="installed_or_pending",
                )
                raise UserError(
                    _(
                        "You are trying to remove a module that is installed or will be installed."
                    )
                )

    def write(self, vals: dict[str, Any]) -> bool:
        if _debug.lifecycle.enabled and "state" in vals:
            _debug.lifecycle(
                "write_state", modules=self.mapped("name"), state=vals["state"]
            )
        res = super().write(vals)
        if not STABLE_CACHE_FIELDS.isdisjoint(vals):
            self.env.registry.clear_cache("stable")
        return res

    def unlink(self) -> bool:
        self.env.registry.clear_cache("stable")
        if _debug.lifecycle.enabled:
            _debug.lifecycle("unlink", modules=self.mapped("name"))
        return super().unlink()

    def _get_domain_modules_to_load(self) -> list[tuple[str, str, str]]:
        return [("state", "=", "installed")]

    @api.model
    def check_external_dependencies(
        self, module_name: str, newstate: str = "to install"
    ) -> None:
        manifest = modules.Manifest.for_addon(module_name)
        if not manifest:
            _debug.logic("external_dependencies.skipped", module=module_name)
            return
        try:
            manifest.check_manifest_dependencies()
        except MissingDependencyError as e:
            msg = {
                "to install": _(
                    'Unable to install module "%(module)s" because an external dependency is not met: %(dependency)s',
                    module=module_name,
                    dependency=e.dependency,
                ),
                "to upgrade": _(
                    'Unable to upgrade module "%(module)s" because an external dependency is not met: %(dependency)s',
                    module=module_name,
                    dependency=e.dependency,
                ),
            }.get(
                newstate,
                _(
                    'Unable to process module "%(module)s" because an external dependency is not met: %(dependency)s',
                    module=module_name,
                    dependency=e.dependency,
                ),
            )

            install_package = None
            if platform.system() == "Linux":
                try:
                    distro = platform.freedesktop_os_release()
                except OSError:
                    distro = {}
                id_likes = {distro.get("ID", ""), *distro.get("ID_LIKE", "").split()}
                if "debian" in id_likes or "ubuntu" in id_likes:
                    if (
                        package := manifest["external_dependencies"]
                        .get("apt", {})
                        .get(e.dependency)
                    ):
                        install_package = f"apt install {package}"

            if install_package:
                msg += _("\nIt can be installed running: %s", install_package)

            _debug.logic(
                "external_dependency.missing",
                module=module_name,
                dependency=e.dependency,
                newstate=newstate,
                apt_hint=bool(install_package),
            )
            raise UserError(msg) from e

    def _update_module_state(
        self, newstate: str, states_to_update: list[str], level: int = 100
    ) -> None:
        if level < 1:
            _debug.logic(
                "module_state.recursion_exhausted", modules=self.mapped("name")
            )
            raise UserError(
                _(
                    "Recursion error in modules dependencies (while processing: %s)!",
                    ", ".join(self.mapped("name")) or "?",
                )
            )

        for module in self:
            if module.state not in states_to_update:
                continue

            update_ids = []
            for dep in module.dependencies_id:
                if dep.state in UNSATISFIABLE_DEPENDENCY_STATES:
                    _debug.logic(
                        "module_state.unsatisfiable_dependency",
                        module=module.name,
                        dependency=dep.name,
                        state=dep.state,
                    )
                    raise UserError(
                        self._get_unsatisfiable_dependency_error(module, dep)
                    )
                if dep.linked_id.state != newstate:
                    update_ids.append(dep.linked_id.id)
            update_mods = self.browse(update_ids)

            update_mods._update_module_state(
                newstate, states_to_update, level=level - 1
            )

            if module.state in states_to_update:
                self.check_external_dependencies(module.name, newstate)
                _debug.lifecycle(
                    "module_state",
                    module=module.name,
                    old=module.state,
                    new=newstate,
                    level=level,
                )
                module.write({"state": newstate})

    def _get_unsatisfiable_dependency_error(self, module: Self, dep: Any) -> str:
        if dep.state == "unknown":
            return _(
                'You try to install module "%(module)s" that depends on module "%(dependency)s".\nBut the latter module is not available in your system.',
                module=module.name,
                dependency=dep.name,
            )
        return _(
            'You try to install module "%(module)s" that depends on module "%(dependency)s".\nBut the latter module cannot be installed.',
            module=module.name,
            dependency=dep.name,
        )

    def _is_auto_install_satisfiable(self) -> bool:
        self.check_singleton()
        return not any(
            dep.state in UNSATISFIABLE_DEPENDENCY_STATES for dep in self.dependencies_id
        )

    @assert_log_admin_access
    def button_install(self) -> dict[str, Any]:
        env_no_prefetch = self.env(
            context=dict(self.env.context, prefetch_fields=False)
        )
        company_countries = env_no_prefetch["res.company"].search([]).country_id
        auto_domain = [
            ("state", "=", "uninstalled"),
            ("auto_install", "=", True),
        ]

        def is_install_required(module):
            if not module._is_auto_install_satisfiable():
                _debug.logic(
                    "auto_install.skipped", module=module.name, reason="unsatisfiable"
                )
                return False
            if module.country_ids and not (module.country_ids & company_countries):
                _debug.logic(
                    "auto_install.skipped", module=module.name, reason="country"
                )
                return False
            triggers = {
                dep.state for dep in module.dependencies_id if dep.auto_install_required
            }
            required = (
                triggers <= AUTO_INSTALL_TRIGGER_STATES and "to install" in triggers
            )
            _debug.logic(
                "auto_install.evaluated",
                module=module.name,
                triggers=sorted(triggers),
                required=required,
            )
            return required

        to_install = self
        rounds = 0  # debuglog
        while to_install:
            rounds += 1  # debuglog
            _debug.pipeline(
                "install_round", round=rounds, modules=to_install.mapped("name")
            )
            to_install._update_module_state("to install", ["uninstalled"])

            if config.get("skip_auto_install"):
                _debug.logic("auto_install.disabled", reason="skip_auto_install")
                to_install = self.browse()
            else:
                to_install = self.search(auto_domain).filtered(is_install_required)

        install_mods = self.search([("state", "in", list(AUTO_INSTALL_TRIGGER_STATES))])
        _debug.pipeline(
            "install_planned", requested=len(self), planned=len(install_mods)
        )

        install_names = {module.name for module in install_mods}
        for module in install_mods:
            for exclusion in module.exclusion_ids:
                if exclusion.name in install_names:
                    _debug.logic(
                        "install.rejected",
                        module=module.name,
                        excluded=exclusion.name,
                        reason="exclusion",
                    )
                    raise UserError(
                        _(
                            'Modules "%(module)s" and "%(incompatible_module)s" are incompatible.',
                            module=module.shortdesc,
                            incompatible_module=exclusion.linked_id.shortdesc,
                        )
                    )

        exclusives = self.env["ir.module.category"].search([("exclusive", "=", True)])
        for category in exclusives:
            categories = category.search([("id", "child_of", category.ids)])
            category_mods = install_mods.filtered(
                lambda mod, categories=categories: mod.category_id in categories
            )
            if category_mods and not any(
                category_mods
                <= (module | module.upstream_dependencies(exclude_states=()))
                for module in category_mods
            ):
                labels = dict(self.fields_get(["state"])["state"]["selection"])
                _debug.logic(
                    "install.rejected",
                    category=category.name,
                    modules=category_mods.mapped("name"),
                    reason="exclusive_category",
                )
                raise UserError(
                    _(
                        'You are trying to install incompatible modules in category "%(category)s":%(module_list)s',
                        category=category.name,
                        module_list="".join(
                            f"\n- {module.shortdesc} ({labels[module.state]})"
                            for module in category_mods
                        ),
                    )
                )

        return dict(ACTION_DICT, name=_("Install"))

    @assert_log_admin_access
    def button_immediate_install(self) -> dict[str, Any]:
        _logger.info("User #%d triggered module installation", self.env.uid)
        if request:
            request.allowed_company_ids = self.env.companies.ids
        return self._button_immediate_function(
            self.env.registry[self._name].button_install
        )

    @assert_log_admin_access
    @api.model
    def button_reset_state(self) -> bool:
        to_install = self.search([("state", "=", "to install")])
        to_install.state = "uninstalled"
        pending = self.search([("state", "in", ("to upgrade", "to remove"))])
        pending.state = "installed"
        _debug.lifecycle(
            "state_reset", to_uninstalled=len(to_install), to_installed=len(pending)
        )
        return True

    @api.model
    def has_pending_module_update(self) -> bool:
        return bool(
            self.sudo().search_count([("state", "in", PENDING_STATES)], limit=1)
        )

    @assert_log_admin_access
    def module_uninstall(self) -> bool:
        modules_to_remove = self.mapped("name")
        _debug.lifecycle("module_uninstall", modules=modules_to_remove)
        self.env["ir.model.data"]._uninstall_module_data(modules_to_remove)
        self.with_context(prefetch_fields=False).write(
            {
                "state": "uninstalled",
                "db_version": False,
                "content_checksum": False,
                "data_file_checksums": False,
            }
        )
        return True

    def _remove_copied_views(self) -> None:
        domain = Domain.OR(Domain("key", "=like", m.name + ".%") for m in self)
        orphans = (
            self.env["ir.ui.view"]
            .with_context(**{"active_test": False, MODULE_UNINSTALL_FLAG: True})
            .search(domain)
        )
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "copied_views.removed", modules=self.mapped("name"), views=len(orphans)
            )
        orphans.unlink()

    def _get_dependency_closure(
        self,
        direction: str,
        known_deps: Self | None,
        exclude_states: tuple[str, ...],
    ) -> Self:
        if not self:
            return self
        known_deps = known_deps or self.browse()
        Module = self.sudo().with_context(active_test=False)
        Dependency = self.env["ir.module.module.dependency"].sudo()
        blocked = set(known_deps.ids) | set(self.ids)
        closure: set[int] = set()
        frontier = Module.browse(self.ids)
        rounds = 0  # debuglog
        while frontier:
            rounds += 1  # debuglog
            if direction == "downstream":
                step = Dependency.search(
                    [("name", "in", frontier.mapped("name"))]
                ).module_id
            else:
                step = Module.search(
                    [
                        (
                            "name",
                            "in",
                            Dependency.search(
                                [("module_id", "in", frontier.ids)]
                            ).mapped("name"),
                        )
                    ]
                )
            step = step.filtered(
                lambda module: (
                    module.state not in exclude_states
                    and module.id not in blocked
                    and module.id not in closure
                )
            )
            closure.update(step.ids)
            frontier = step
        _debug.perf.count(
            "dependency_closure.computed",
            direction=direction,
            seeds=len(self),
            known=len(known_deps),
            closure=len(closure),
            rounds=rounds,
        )
        return known_deps | self.browse(sorted(closure))

    def downstream_dependencies(
        self,
        known_deps: Self | None = None,
        exclude_states: tuple[str, ...] = (
            "uninstalled",
            "uninstallable",
            "to remove",
        ),
    ) -> Self:
        return self._get_dependency_closure("downstream", known_deps, exclude_states)

    def upstream_dependencies(
        self,
        known_deps: Self | None = None,
        exclude_states: tuple[str, ...] = (
            "installed",
            "uninstallable",
            "to remove",
        ),
    ) -> Self:
        return self._get_dependency_closure("upstream", known_deps, exclude_states)

    def _next_todo_action(self) -> dict[str, Any]:
        Todos = self.env["ir.actions.todo"]
        _logger.info("getting next %s", Todos)
        active_todo = Todos.search([("state", "=", "open")], limit=1)
        if active_todo:
            _logger.info('next action is "%s"', active_todo.name)
            _debug.logic("next_action.todo", todo=active_todo.id)
            return active_todo.action_launch()
        _debug.logic("next_action.home")
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/odoo",
        }

    def _has_pending_module_operation(self) -> bool:
        with self.env.registry.cursor() as check_cr:
            check_cr.execute(
                SQL(
                    "SELECT FROM ir_module_module WHERE state IN %s LIMIT 1",
                    tuple(PENDING_STATES),
                )
            )
            pending = bool(check_cr.rowcount)
            _debug.logic("pending_operation.checked", pending=pending)
            return pending

    def _lock_against_concurrent_module_operations(self) -> None:
        busy = _(
            "Odoo is currently processing another module operation.\n"
            "Please try again later or contact your system administrator."
        )
        cr = self.env.cr
        cr.execute("SET LOCAL lock_timeout = '3s'")
        try:
            cr.execute("LOCK ir_module_module IN EXCLUSIVE MODE")
        except psycopg.OperationalError:
            cr.rollback()
            _debug.logic("module_lock_busy", reason="table_lock_timeout")
            raise UserError(busy) from None

        if self._has_pending_module_operation():
            _debug.logic("module_lock_busy", reason="pending_operation")
            raise UserError(busy)

        try:
            cr.execute("SELECT FROM ir_cron FOR UPDATE")
        except psycopg.OperationalError:
            cr.rollback()
            _debug.logic("module_lock_busy", reason="cron_lock_timeout")
            raise UserError(
                _(
                    "Odoo is currently processing a scheduled action.\n"
                    "Module operations are not possible at this time, "
                    "please try again later or contact your system administrator."
                )
            ) from None
        if _debug.lifecycle.enabled:
            _debug.lifecycle("module_lock.acquired", modules=self.mapped("name"))

    def _button_immediate_function(
        self, function: Callable[..., Any]
    ) -> dict[str, Any]:
        if not self.env.registry.ready:
            _debug.logic("immediate_function.rejected", reason="registry_not_ready")
            raise UserError(
                _(
                    "Immediate module operations cannot be performed on an init or non-loaded registry. Please use button_install instead."
                )
            )

        if modules.module.current_test:
            _debug.logic("immediate_function.rejected", reason="inside_test")
            msg = (
                "Module operations inside tests are not transactional and thus forbidden.\n"
                "If you really need to perform module operations to test a specific behavior, it "
                "is best to write it as a standalone script, and ask the runbot/metastorm team "
                "for help."
            )
            raise RuntimeError(msg)

        self._lock_against_concurrent_module_operations()
        _debug.pipeline(
            "immediate_function",
            function=function.__name__,
            modules=self.mapped("name"),
        )
        function(self)

        self.env.cr.commit()
        with _debug.perf("registry_reload", db=self.env.cr.dbname):
            registry = modules.registry.Registry.new(
                self.env.cr.dbname, update_module=True
            )
        self.env.cr.commit()
        if request and request.registry is self.env.registry:
            request.env.cr.reset()
            request.registry = request.env.registry
            if request.env.registry is not registry:
                raise RuntimeError(
                    "Registry mismatch after module installation: request registry was not refreshed"
                )
        self.env.cr.reset()
        if self.env.registry is not registry:
            raise RuntimeError(
                "Registry mismatch after module installation: env registry was not refreshed"
            )

        next_action = self.env["ir.module.module"]._next_todo_action() or {}
        _debug.pipeline(
            "immediate_function.done",
            function=function.__name__,
            next_action=next_action.get("type"),
        )
        if next_action.get("type") != "ir.actions.act_window_close":
            return next_action

        menu = self.env["ir.ui.menu"].search([("parent_id", "=", False)])[:1]
        return {
            "type": "ir.actions.client",
            "tag": "reload",
            "params": {"menu_id": menu.id},
        }

    @assert_log_admin_access
    def button_immediate_uninstall(self) -> dict[str, Any]:
        _logger.info("User #%d triggered module uninstallation", self.env.uid)
        return self._button_immediate_function(
            self.env.registry[self._name].button_uninstall
        )

    @assert_log_admin_access
    def button_uninstall(self) -> dict[str, Any]:
        un_installable_modules = set(config["server_wide_modules"]) & set(
            self.mapped("name")
        )
        if un_installable_modules:
            _debug.logic(
                "uninstall.rejected",
                modules=sorted(un_installable_modules),
                reason="server_wide",
            )
            raise UserError(
                _(
                    "Those modules cannot be uninstalled: %s",
                    ", ".join(un_installable_modules),
                )
            )
        if any(
            state not in ("installed", "to upgrade") for state in self.mapped("state")
        ):
            _debug.logic(
                "uninstall.rejected",
                modules=self.mapped("name"),
                reason="not_installed",
            )
            raise UserError(
                _(
                    "One or more of the selected modules have already been uninstalled, if you "
                    "believe this to be an error, you may try again later or contact support."
                )
            )
        deps = self.downstream_dependencies()
        _debug.lifecycle(
            "uninstall_planned",
            modules=self.mapped("name"),
            dependents=deps.mapped("name"),
        )
        (self + deps).write({"state": "to remove"})
        return dict(ACTION_DICT, name=_("Uninstall"))

    @assert_log_admin_access
    def button_uninstall_wizard(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.act_window",
            "target": "new",
            "name": _("Uninstall module"),
            "view_mode": "form",
            "res_model": "base.module.uninstall",
            "context": {"default_module_ids": self.ids},
        }

    @assert_log_admin_access
    def button_immediate_upgrade(self) -> dict[str, Any]:
        return self._button_immediate_function(
            self.env.registry[self._name].button_upgrade
        )

    def _upgrade_cascade(self) -> list[Self]:
        Dependency = self.env["ir.module.module.dependency"]
        todo = list(self)
        seen_ids = set(self.ids)
        if "base" in self.mapped("name"):
            others = self.search(
                [
                    ("state", "=", "installed"),
                    ("name", "!=", STUDIO_CUSTOMIZATION),
                    ("id", "not in", self.ids),
                ]
            )
            todo.extend(others)
            seen_ids.update(others._ids)
            _debug.pipeline("upgrade_cascade.base_pulls_installed", others=len(others))

        dependents_by_name = defaultdict(list)
        for dep in Dependency.search([]):
            dependents_by_name[dep.name].append(dep.module_id)

        i = 0
        while i < len(todo):
            module = todo[i]
            i += 1
            if module.state not in ("installed", "to upgrade"):
                _debug.logic(
                    "upgrade.rejected",
                    module=module.name,
                    state=module.state,
                    reason="not_installed",
                )
                raise UserError(
                    _(
                        "Cannot upgrade module “%s”. It is not installed.",
                        module.name,
                    )
                )
            if self._is_installable(module.name):
                self.check_external_dependencies(module.name, "to upgrade")
            for dependent in dependents_by_name.get(module.name, ()):
                if (
                    dependent.id not in seen_ids
                    and dependent.state == "installed"
                    and dependent.name != STUDIO_CUSTOMIZATION
                ):
                    seen_ids.add(dependent.id)
                    todo.append(dependent)
        _debug.pipeline("upgrade_cascade", requested=len(self), cascade=len(todo))
        return todo

    def _get_module_ids_to_upgrade(self, cascade: list[Self]) -> list[int]:
        if not config["skip_unchanged_modules"] or not column_exists(
            self.env.cr, "ir_module_module", "content_checksum"
        ):
            _debug.logic(
                "upgrade_checksum.disabled",
                cascade=len(cascade),
                reason="config"
                if not config["skip_unchanged_modules"]
                else "no_column",
            )
            return [module.id for module in cascade]

        self.env.cr.execute(
            "SELECT id, content_checksum, data_file_checksums FROM ir_module_module"
            " WHERE content_checksum IS NOT NULL"
        )
        stamped, overridden_modules = {}, {}
        for module_id, checksum, data_files in self.env.cr.fetchall():
            stamped[module_id] = checksum
            overridden_modules[module_id] = _modules_whose_records_it_writes(data_files)
        requested_ids = set(self.ids)
        marked_ids, unchanged = [], []
        for module in cascade:
            stored = stamped.get(module.id)
            if (
                module.id not in requested_ids
                and stored is not None
                and get_module_content_checksum(module.name) == stored
            ):
                unchanged.append(module)
            else:
                marked_ids.append(module.id)
        # An unchanged module whose data writes a record another module
        # declares (website_sale re-activating sale_team.salesteam_website_sales) has its
        # effect in the load order, not in its bytes: once the declaring module
        # reloads, the override must be re-applied or it is silently reverted.
        # The per-file skip in modules/loading.py already refuses to skip such
        # a file; a module that is not loaded at all never reaches it.
        marked_names = {m.name for m in cascade if m.id in set(marked_ids)}
        while True:
            reloaded = [
                m
                for m in unchanged
                if overridden_modules.get(m.id) is None
                or overridden_modules[m.id] & marked_names
            ]
            if not reloaded:
                break
            for module in reloaded:
                _logger.info(
                    "upgrade cascade: %s is unchanged but writes records of a "
                    "module being upgraded (%s); re-applying it in order",
                    module.name,
                    ", ".join(
                        sorted(
                            (overridden_modules.get(module.id) or set()) & marked_names
                        )
                    )
                    or "unknown, no data-file checksums stored yet",
                )
                _debug.logic("upgrade_checksum.reapplied", module=module.name)
                marked_ids.append(module.id)
                marked_names.add(module.name)
                unchanged.remove(module)
        skipped = len(unchanged)
        if skipped:
            _logger.info(
                "upgrade cascade: %d modules to upgrade, %d unchanged "
                "modules left as installed "
                "(--upgrade-unchanged-modules to force)",
                len(marked_ids),
                skipped,
            )
        _debug.logic("upgrade_checksum_skip", marked=len(marked_ids), skipped=skipped)
        return marked_ids

    def _get_uninstalled_dependency_names(self, cascade: list[Self]) -> list[str]:
        names = []
        for module in cascade:
            if not self._is_installable(module.name):
                continue
            for dep in module.dependencies_id:
                if dep.state == "unknown":
                    _debug.logic(
                        "upgrade.rejected",
                        module=module.name,
                        dependency=dep.name,
                        reason="unknown_dependency",
                    )
                    raise UserError(
                        _(
                            "You try to upgrade the module %(module)s that depends on the module: %(dependency)s.\nBut this module is not available in your system.",
                            module=module.name,
                            dependency=dep.name,
                        )
                    )
                if dep.state == "uninstalled":
                    names.append(dep.name)
        _debug.logic("upgrade.uninstalled_dependencies", count=len(names))
        return names

    @assert_log_admin_access
    def button_upgrade(self) -> dict[str, Any] | None:
        if not self:
            _debug.logic("upgrade.skipped", reason="empty_recordset")
            return None
        if _debug.pipeline.enabled:
            _debug.pipeline("upgrade.requested", modules=self.mapped("name"))
        self.update_list()
        cascade = self._upgrade_cascade()
        self.browse(self._get_module_ids_to_upgrade(cascade)).write(
            {"state": "to upgrade"}
        )
        if uninstalled_dep_names := self._get_uninstalled_dependency_names(cascade):
            _debug.pipeline(
                "upgrade.installing_dependencies", modules=uninstalled_dep_names
            )
            self.search([("name", "in", uninstalled_dep_names)]).button_install()
        return dict(ACTION_DICT, name=_("Apply Schedule Upgrade"))

    @staticmethod
    def get_values_from_terp(terp: dict[str, Any] | Manifest) -> dict[str, Any]:
        return {
            "description": dedent(terp.get("description", "")),
            "shortdesc": terp.get("name", ""),
            "author": terp.get("author", "Unknown"),
            "maintainer": terp.get("maintainer", False),
            "contributors": ", ".join(terp.get("contributors", [])) or False,
            "website": terp.get("website", ""),
            "license": terp.get("license", "LGPL-3"),
            "sequence": terp.get("sequence", 100),
            "application": terp.get("application", False),
            "auto_install": terp.get("auto_install", False) is not False,
            "icon": terp.get("icon", False),
            "summary": terp.get("summary", ""),
            "url": terp.get("url") or terp.get("live_test_url", ""),
            "to_buy": False,
        }

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        modules = super().create(vals_list)
        module_metadata_list = [
            {
                "name": f"module_{module.name}",
                "model": "ir.module.module",
                "module": "base",
                "res_id": module.id,
                "noupdate": True,
            }
            for module in modules
        ]
        self.env["ir.model.data"].create(module_metadata_list)
        self.env.registry.clear_cache("stable")
        _debug.lifecycle("create", modules=modules.mapped("name"))
        return modules

    @assert_log_admin_access
    @api.model
    def update_list(self) -> UpdateListResult:
        from odoo.addons.base.models.assetsbundle import AssetsBundle

        AssetsBundle.invalidate_addon_scan_cache()

        updated = added = 0

        default_version = modules.adapt_version("1.0")
        known_mods = self.with_context(lang=None).search([])
        known_mods_names = {mod.name: mod for mod in known_mods}
        auto_install_requirements: dict[int, Collection[str]] = {}
        category_cache: dict[str, int] = {}

        for manifest in modules.Manifest.get_all_addon_manifests():
            mod = known_mods_names.get(manifest.name)
            values = self.get_values_from_terp(manifest)

            if mod:
                updated_values = {}
                for key in values:
                    old = getattr(mod, key)
                    if (old or values[key]) and values[key] != old:
                        updated_values[key] = values[key]
                if manifest.get("installable", True) and mod.state == "uninstallable":
                    updated_values["state"] = "uninstalled"
                if mod.db_version and parse_version(
                    manifest.get("version", default_version)
                ) > parse_version(mod.db_version):
                    updated += 1
                if updated_values:
                    _debug.lifecycle(
                        "update_list.module_updated",
                        module=manifest.name,
                        fields=sorted(updated_values),
                    )
                    mod.write(updated_values)
            else:
                state = (
                    "uninstalled"
                    if manifest.get("installable", True)
                    else "uninstallable"
                )
                _debug.lifecycle(
                    "update_list.module_discovered", module=manifest.name, state=state
                )
                mod = self.create(dict(name=manifest.name, state=state, **values))
                added += 1

            mod._update_from_terp(manifest, category_cache)
            auto_install_requirements[mod.id] = manifest.get("auto_install") or ()

        self._sync_auto_install_required(auto_install_requirements)

        _debug.pipeline(
            "update_list", known=len(known_mods), updated=updated, added=added
        )
        return UpdateListResult(updated=updated, added=added)

    def _update_from_terp(
        self,
        terp: dict[str, Any] | Manifest,
        category_cache: dict[str, int] | None = None,
    ) -> None:
        self._update_dependencies(terp.get("depends", []))
        self._update_countries(terp.get("countries", []))
        self._update_exclusions(terp.get("excludes", []))
        self._update_category(terp.get("category", "Uncategorized"), category_cache)

    def _sync_link_rows(
        self,
        table: str,
        column: str,
        existing: set,
        needed: set,
        cast: SQL,
    ) -> bool:
        self.check_singleton()
        cr = self.env.cr
        if to_add := sorted(needed - existing):
            cr.execute(
                SQL(
                    "INSERT INTO %s (module_id, %s) SELECT %s, unnest(%s::%s)",
                    SQL.identifier(table),
                    SQL.identifier(column),
                    self.id,
                    to_add,
                    cast,
                )
            )
        if to_remove := sorted(existing - needed):
            cr.execute(
                SQL(
                    "DELETE FROM %s WHERE module_id = %s AND %s = ANY(%s)",
                    SQL.identifier(table),
                    self.id,
                    SQL.identifier(column),
                    to_remove,
                )
            )
        if _debug.perf.enabled and (to_add or to_remove):
            _debug.perf.count(
                "link_rows.synced",
                module=self.name,
                table=table,
                added=len(to_add),
                removed=len(to_remove),
            )
        return bool(to_add or to_remove)

    def _update_dependencies(self, depends: list[str] | None = None) -> None:
        self.env["ir.module.module.dependency"].flush_model()
        if self._sync_link_rows(
            "ir_module_module_dependency",
            "name",
            {dep.name for dep in self.dependencies_id},
            set(depends or []),
            SQL("varchar[]"),
        ):
            self.invalidate_recordset(["dependencies_id"])

    @api.model
    def _sync_auto_install_required(
        self, requirements: dict[int, Collection[str]]
    ) -> None:
        if not requirements:
            _debug.logic("auto_install_required.skipped", reason="no_requirements")
            return
        Dependency = self.env["ir.module.module.dependency"]
        Dependency.flush_model(["auto_install_required"])
        values = SQL(", ").join(
            SQL("(%s, %s::varchar[])", module_id, list(names or ()))
            for module_id, names in requirements.items()
        )
        with _debug.perf(
            "auto_install_required.synced", cr=self.env.cr, modules=len(requirements)
        ) as span:
            self.env.cr.execute(
                SQL(
                    """ UPDATE ir_module_module_dependency d
                        SET auto_install_required = (d.name = ANY(v.required))
                        FROM (VALUES %s) AS v(module_id, required)
                        WHERE d.module_id = v.module_id
                          AND d.auto_install_required
                              IS DISTINCT FROM (d.name = ANY(v.required)) """,
                    values,
                )
            )
            span.set(rows=self.env.cr.rowcount)
        Dependency.invalidate_model(["auto_install_required"])

    def _update_countries(self, countries: tuple[str, ...] | list[str] = ()) -> None:
        existing = set(self.country_ids.ids)
        id_by_code = self.env["res.country"]._get_id_by_code()
        needed = {
            country_id
            for code in countries
            if (country_id := id_by_code.get(code.upper()))
        }
        if _debug.logic.enabled and len(needed) != len(countries):
            _debug.logic(
                "countries.unresolved",
                module=self.name,
                codes=[code for code in countries if code.upper() not in id_by_code],
            )
        if self._sync_link_rows(
            "module_country", "country_id", existing, needed, SQL("integer[]")
        ):
            self.invalidate_recordset(["country_ids"])
            self.env["res.company"].invalidate_model(["uninstalled_l10n_module_ids"])

    def _update_exclusions(self, excludes: list[str] | None = None) -> None:
        self.env["ir.module.module.exclusion"].flush_model()
        if self._sync_link_rows(
            "ir_module_module_exclusion",
            "name",
            {excl.name for excl in self.exclusion_ids},
            set(excludes or []),
            SQL("varchar[]"),
        ):
            self.invalidate_recordset(["exclusion_ids"])

    def _update_category(
        self,
        category: str = "Uncategorized",
        category_cache: dict[str, int] | None = None,
    ) -> None:
        current_category = self.category_id
        seen = set()
        while current_category:
            seen.add(current_category.id)
            if current_category.parent_id.id in seen:
                current_category.parent_id = False
                _debug.lifecycle(
                    "category.loop_fixed",
                    module=self.name,
                    category=current_category.id,
                )
                _logger.warning(
                    "category %r ancestry loop has been detected and fixed",
                    current_category,
                )
            current_category = current_category.parent_id

        cat_id = modules.db.get_or_create_category_id(
            self.env.cr, category.split("/"), category_cache
        )
        if cat_id != self.category_id.id:
            _debug.lifecycle(
                "category.changed",
                module=self.name,
                old=self.category_id.id,
                new=cat_id,
            )
            self.write({"category_id": cat_id})

    def _update_translations(
        self,
        filter_lang: list[str] | str | None = None,
        overwrite: bool = False,
    ) -> None:
        if not filter_lang:
            langs = self.env["res.lang"].get_installed()
            filter_lang = [code for code, _ in langs]
        elif not isinstance(filter_lang, list | tuple):
            filter_lang = [filter_lang]

        update_mods = self.filtered(
            lambda r: r.state in ("installed", "to install", "to upgrade")
        )
        mod_dict = {mod.name: mod.dependencies_id.mapped("name") for mod in update_mods}
        mod_names = topological_sort(mod_dict)
        _debug.pipeline(
            "translations.update",
            requested=len(self),
            modules=len(mod_names),
            langs=len(filter_lang),
            overwrite=overwrite,
        )
        self._load_module_terms(mod_names, filter_lang, overwrite)

    def _check(self) -> None:
        for module in self:
            if not module.description_html:
                _logger.warning("module %s: description is empty!", module.name)

    def _get(self, name: str) -> Self:
        module_id = self._get_id(name) if name else False
        return self.browse(module_id).sudo()

    @tools.ormcache("name", cache="stable")
    def _get_id(self, name: str) -> int | None:
        self.flush_model(["name"])
        self.env.cr.execute("SELECT id FROM ir_module_module WHERE name=%s", (name,))
        result = self.env.cr.fetchone()
        _debug.perf.count("module_id.cache_miss", name=name, found=bool(result))
        return result[0] if result else None

    @api.model
    @tools.ormcache(cache="stable")
    def _get_installed_module_ids(self) -> dict[str, int]:
        installed = {
            module.name: module.id
            for module in self.sudo().search([("state", "=", "installed")])
        }
        _debug.perf.count("installed_module_ids.cache_miss", count=len(installed))
        return installed

    @api.model
    def search_panel_select_range(
        self, field_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        if field_name == "category_id":
            enable_counters = kwargs.get("enable_counters", False)
            domain = Domain(
                [
                    ("parent_id", "=", False),
                    "|",
                    ("module_ids.application", "!=", False),
                    ("child_ids.module_ids", "!=", False),
                ]
            )

            excluded_xmlids = [
                "base.module_category_website_theme",
                "base.module_category_theme",
            ]
            if not self.env.user.has_group("base.group_no_one"):
                excluded_xmlids.append("base.module_category_hidden")

            excluded_category_ids = []
            for excluded_xmlid in excluded_xmlids:
                categ = self.env.ref(excluded_xmlid, False)
                if not categ:
                    continue
                excluded_category_ids.append(categ.id)

            if excluded_category_ids:
                domain &= Domain("id", "not in", excluded_category_ids)

            records = self.env["ir.module.category"].search_read(
                domain, ["display_name"], order="sequence"
            )
            _debug.logic(
                "search_panel.categories",
                records=len(records),
                excluded=len(excluded_category_ids),
                counters=enable_counters,
            )

            if enable_counters and records:
                self._count_modules_per_root_category(
                    records, excluded_category_ids, kwargs
                )

            return {
                "parent_field": "parent_id",
                "values": records,
            }

        return super().search_panel_select_range(field_name, **kwargs)

    @api.model
    def _count_modules_per_root_category(
        self,
        records: list[dict[str, Any]],
        excluded_category_ids: list[int],
        kwargs: dict[str, Any],
    ) -> None:
        root_ids = [record["id"] for record in records]
        Category = self.env["ir.module.category"]
        parent_by_id = {
            category.id: category.parent_id.id
            for category in Category.search([("id", "child_of", root_ids)])
        }
        roots = set(root_ids)

        def get_root_category_id(category_id: int) -> int | None:
            node, seen = category_id, set()
            while node and node not in roots and node not in seen:
                seen.add(node)
                node = parent_by_id.get(node)
            return node if node in roots else None

        domain = Domain.AND(
            [
                kwargs.get("search_domain", []),
                kwargs.get("category_domain", []),
                kwargs.get("filter_domain", []),
                [
                    ("category_id", "child_of", root_ids),
                    ("category_id", "not in", excluded_category_ids),
                ],
            ]
        )
        counts: defaultdict[int, int] = defaultdict(int)
        for category, count in self._read_group(
            domain, groupby=["category_id"], aggregates=["__count"]
        ):
            if root := get_root_category_id(category.id):
                counts[root] += count
        _debug.perf.count(
            "category_counts.computed", roots=len(root_ids), counted=len(counts)
        )
        for record in records:
            record["__count"] = counts[record["id"]]

    @api.model
    def _load_module_terms(
        self, module_names: list[str], langs: list[str], overwrite: bool = False
    ) -> None:
        translation_importer = TranslationImporter(self.env.cr, verbose=False)

        with _debug.perf(
            "load_module_terms",
            cr=self.env.cr,
            modules=len(module_names),
            langs=langs,
            overwrite=overwrite,
        ):
            self._load_module_terms_into(translation_importer, module_names, langs)
            translation_importer.save(overwrite=overwrite)

    def _load_module_terms_into(
        self,
        translation_importer: TranslationImporter,
        module_names: list[str],
        langs: list[str],
    ) -> None:
        for module_name in module_names:
            if not Manifest.for_addon(module_name, display_warning=False):
                _debug.logic("terms.module_skipped", module=module_name)
                continue
            code_translations.clear(module_name)
            data_paths = list(get_datafile_translation_path(module_name))
            for lang in langs:
                seen_before = set(translation_importer.imported_langs)
                for po_path in get_po_paths(module_name, lang):
                    _logger.info(
                        "module %s: loading translation file %s for language %s",
                        module_name,
                        po_path,
                        lang,
                    )
                    translation_importer.load_file(po_path, lang)
                for data_path in data_paths:
                    translation_importer.load_file(data_path, lang, module=module_name)
                imported_here = translation_importer.imported_langs - seen_before
                if lang != "en_US" and lang not in imported_here:
                    _debug.logic("terms.lang_missing", module=module_name, lang=lang)
                    _logger.info(
                        "module %s: no translation for language %s",
                        module_name,
                        lang,
                    )

    @api.model
    def _extract_resource_attachment_translations(
        self, module: str, lang: str
    ) -> Iterator[Any]:
        yield from ()
