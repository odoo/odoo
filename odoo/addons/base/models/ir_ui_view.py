import ast
import collections
import functools
import inspect
import logging
import pprint
import re
import uuid
from contextlib import suppress
import typing
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Self

from lxml import etree
from lxml.builder import E
from lxml.etree import _Element  # noqa: TC003 — runtime import required (PEP 649)
from markupsafe import Markup

from odoo import api, fields, models, tools
from odoo.exceptions import (
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.fields import Domain
from odoo.modules.module import get_resource_from_path
from odoo.tools import SQL, _, config, partition, unique
from odoo.tools.convert import _fix_multiple_roots
from odoo.tools.misc import ConstantMapping, file_path
from odoo.tools.template_inheritance import apply_inheritance_specs, locate_node
from odoo.tools.translate import TRANSLATED_ATTRS, xml_translate
from odoo.orm._typing import ValuesType
from odoo.tools.view_validation import (
    get_dict_asts,
    get_domain_value_names,
    get_expression_field_names,
    valid_view,
)

from .ir_ui_view_name_manager import NameManager

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

_logger = logging.getLogger(__name__)

MOVABLE_BRANDING = [
    "data-oe-model",
    "data-oe-id",
    "data-oe-field",
    "data-oe-xpath",
    "data-oe-source-id",
]
VIEW_MODIFIERS = ("column_invisible", "invisible", "readonly", "required")

# Some views have a js compiler that generates an owl template from the arch. In that template,
# `__comp__` is a reserved keyword giving access to the component instance (e.g. the form renderer
# or the kanban record). However, we don't want to see implementation details leaking in archs, so
# we use the following regex to detect the use of `__comp__` in dynamic attributes, to forbid it.
COMP_REGEX = r"(^|[^\w])\s*__comp__\s*([^\w]|$)"

ref_re = re.compile(
    r"""
# first match 'form_view_ref' key, backrefs are used to handle single or
# double quoting of the value
(['"])(?P<view_type>\w+_view_ref)\1
# colon separator (with optional spaces around)
\s*:\s*
# open quote for value
(['"])
(?P<view_id>
    # we'll just match stuff which is normally part of an xid:
    # word and "." characters
    [.\w]+
)
# close with same quote as opening
\3
""",
    re.VERBOSE,
)


def att_names(name: str) -> Generator[str]:
    yield name
    yield f"t-att-{name}"
    yield f"t-attf-{name}"


def _hasclass(context: Any, *cls: str) -> bool:
    """Checks if the context node has all the classes passed as arguments"""
    node_classes = set(context.context_node.attrib.get("class", "").split())
    return node_classes.issuperset(cls)


def get_view_arch_from_file(filepath: str, xmlid: str) -> str | None:
    if "." not in xmlid:
        raise ValueError(f"Invalid xmlid {xmlid!r}: expected 'module.name' format")
    module, view_id = xmlid.split(".", 1)

    xpath = f"//*[@id='{xmlid}' or @id='{view_id}']"
    # when view is created from model with inheritS of ir_ui_view, the
    # xmlid has been suffixed by '_ir_ui_view'. We need to also search
    # for views without this prefix.
    if view_id.endswith("_ir_ui_view"):
        # len('_ir_ui_view') == 11  # noqa: ERA001
        xpath = xpath[:-1] + f" or @id='{xmlid[:-11]}' or @id='{view_id[:-11]}']"

    document = etree.parse(filepath)
    for node in document.xpath(xpath):
        if node.tag == "record":
            field_arch = node.find('field[@name="arch"]')
            if field_arch is not None:
                _fix_multiple_roots(field_arch)
                inner = "".join(
                    etree.tostring(child, encoding="unicode")
                    for child in field_arch.iterchildren()
                )
                return (field_arch.text or "") + inner

            field_view = node.find('field[@name="view_id"]')
            if field_view is not None:
                ref = field_view.attrib.get("ref")
                if ref is None:
                    return None
                ref_module, _, ref_view_id = ref.rpartition(".")
                ref_xmlid = f"{ref_module or module}.{ref_view_id}"
                return get_view_arch_from_file(filepath, ref_xmlid)

            return None

        elif node.tag == "template":
            # The following dom operations has been copied from convert.py's _tag_template()
            if not node.get("inherit_id"):
                node.set("t-name", xmlid)
                node.tag = "t"
            else:
                node.tag = "data"
            node.attrib.pop("id", None)
            return etree.tostring(node, encoding="unicode")

    _logger.warning(
        "Could not find view arch definition in file '%s' for xmlid '%s'",
        filepath,
        xmlid,
    )
    return None


xpath_utils = etree.FunctionNamespace(None)
xpath_utils["hasclass"] = _hasclass

TRANSLATED_ATTRS_RE = re.compile(rf"@({'|'.join(TRANSLATED_ATTRS)})\b")
WRONGCLASS = re.compile(r"(@class\s*=|=\s*@class|contains\(@class)")

# Pre-compiled XPath expressions for view processing hot paths (lxml 6.0 best practice).
# ETXPath objects are document-independent and thread-safe, so module-level constants
# avoid re-compiling the same expressions on every view render/validation call.
_xpath_position = etree.ETXPath("//*[@position]")
_xpath_attrs = etree.ETXPath("//*[@attrs]")
_xpath_states = etree.ETXPath("//*[@states]")
_xpath_validate = etree.ETXPath("//*[@__validate__]")
_xpath_groups_key = etree.ETXPath("//*[@__groups_key__]")
_xpath_model_access = etree.ETXPath("//*[@model_access_rights]")
_xpath_groups = etree.ETXPath("//*[@groups]")
_xpath_debug = etree.ETXPath("//*[@__debug__]")
_xpath_descendant_field = etree.ETXPath("./*[descendant::field]")


class IrUiView(models.Model):
    _name = "ir.ui.view"
    _description = "View"
    _order = "priority,name,id"
    _allow_sudo_commands = False

    name = fields.Char(string="View Name", required=True)
    model = fields.Char(index=True)
    key = fields.Char(index="btree_not_null")
    priority = fields.Integer(string="Sequence", default=16, required=True)
    type = fields.Selection(
        [
            ("list", "List"),
            ("form", "Form"),
            ("graph", "Graph"),
            ("pivot", "Pivot"),
            ("calendar", "Calendar"),
            ("kanban", "Kanban"),
            ("search", "Search"),
            ("qweb", "QWeb"),
        ],
        string="View Type",
    )
    arch = fields.Text(
        compute="_compute_arch",
        inverse="_inverse_arch",
        string="View Architecture",
        help="""This field should be used when accessing view arch. It will use translation.
                               Note that it will read `arch_db` or `arch_fs` if in dev-xml mode.""",
    )
    arch_base = fields.Text(
        compute="_compute_arch_base",
        inverse="_inverse_arch_base",
        string="Base View Architecture",
        help="This field is the same as `arch` field without translations",
    )
    arch_db = fields.Text(
        string="Arch Blob",
        translate=xml_translate,
        help="This field stores the view arch.",
    )
    arch_fs = fields.Char(
        string="Arch Filename",
        help="""File from where the view originates.
                                                          Useful to (hard) reset broken views or to read arch from file in dev-xml mode.""",
    )
    arch_updated = fields.Boolean(string="Modified Architecture")
    arch_prev = fields.Text(
        string="Previous View Architecture",
        help="""This field will save the current `arch_db` before writing on it.
                                                                         Useful to (soft) reset a broken view.""",
    )
    inherit_id = fields.Many2one(
        "ir.ui.view", string="Inherited View", ondelete="restrict", index=True
    )
    inherit_children_ids = fields.One2many(
        "ir.ui.view", "inherit_id", string="Views which inherit from this one"
    )
    model_data_id = fields.Many2one(
        "ir.model.data",
        string="Model Data",
        compute="_compute_model_data_id",
        search="_search_model_data_id",
    )
    xml_id = fields.Char(
        string="External ID",
        compute="_compute_xml_id",
        help="ID of the view defined in xml file",
    )
    group_ids = fields.Many2many(
        "res.groups",
        "ir_ui_view_group_rel",
        "view_id",
        "group_id",
        string="Groups",
        help="If this field is empty, the view applies to all users. Otherwise, the view applies to the users of those groups only.",
    )
    mode = fields.Selection(
        [("primary", "Base view"), ("extension", "Extension View")],
        string="View inheritance mode",
        default="primary",
        required=True,
        help="Only applies if this view inherits from an other one"
        " (inherit_id is not False/Null).\n\n"
        "* if extension (default), if this view is requested the closest primary view"
        " is looked up (via inherit_id), then all views inheriting from it with this"
        " view's model are applied\n"
        "* if primary, the closest primary view is fully resolved (even if it uses a"
        " different model than this one), then this view's inheritance specs"
        " (<xpath/>) are applied, and the result is used as if it were this view's"
        " actual arch.",
    )

    warning_info = fields.Html(
        string="Warning information", compute="_compute_warning_info"
    )

    # The "active" field is not updated during updates if <template> is used
    # instead of <record> to define the view in XML, see _tag_template. For
    # qweb views, you should not rely on the active field being updated anyway
    # as those views, if used in frontend layouts, can be duplicated (see COW)
    # and will thus always require upgrade scripts if you really want to change
    # the default value of their "active" field.
    active = fields.Boolean(
        default=True,
        help="If this view is inherited,\n\n"
        "* if True, the view always extends its parent\n"
        "* if False, the view currently does not extend its parent but can be enabled",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model of the view",
        compute="_compute_model_id",
        inverse="_inverse_compute_model_id",
    )

    invalid_locators = fields.Json(compute="_compute_invalid_locators")

    @api.depends("arch_db", "arch_fs", "arch_updated")
    @api.depends_context(
        "read_arch_from_file", "lang", "edit_translations", "check_translations"
    )
    def _compute_arch(self) -> None:
        def resolve_external_ids(arch_fs: str, view_xml_id: str) -> str:
            def replacer(m: re.Match[str]) -> str:
                xmlid = m.group("xmlid")
                if "." not in xmlid:
                    xmlid = f"{view_xml_id.split('.', maxsplit=1)[0]}.{xmlid}"
                return m.group("prefix") + str(
                    self.env["ir.model.data"]._xmlid_to_res_id(xmlid)
                )

            return re.sub(r"(?P<prefix>[^%])%\((?P<xmlid>.*?)\)[ds]", replacer, arch_fs)

        lang = self.env.lang or "en_US"
        env_en = self.with_context(
            edit_translations=None, lang="en_US", check_translations=True
        ).env
        env_lang = self.with_context(lang=lang, check_translations=True).env
        field_arch_db = self._fields["arch_db"]
        read_from_file_ctx = self.env.context.get("read_arch_from_file")
        dev_xml = "xml" in config["dev_mode"]
        for view in self:
            arch_fs = None
            read_file = read_from_file_ctx or (dev_xml and not view.arch_updated)
            if read_file and view.arch_fs and (view.xml_id or view.key):
                xml_id = view.xml_id or view.key
                try:
                    # reading the file will raise an OSError if it is unreadable
                    arch_fs = get_view_arch_from_file(
                        file_path(view.arch_fs, check_exists=False), xml_id
                    )
                except OSError:
                    _logger.warning(
                        "View %s: Full path [%s] cannot be found.",
                        xml_id,
                        view.arch_fs,
                    )
                    arch_fs = False

                # replace %(xml_id)s, %(xml_id)d, %%(xml_id)s, %%(xml_id)d by the res_id
                if arch_fs:
                    arch_fs = resolve_external_ids(arch_fs, xml_id).replace("%%", "%")
                    translation_dictionary = field_arch_db.get_translation_dictionary(
                        view.with_env(env_en).arch_db,
                        {lang: view.with_env(env_lang).arch_db},
                    )
                    arch_fs = field_arch_db.translate(
                        lambda term, td=translation_dictionary, _lang=lang: td[term][
                            _lang
                        ],
                        arch_fs,
                    )
            view.arch = arch_fs or view.arch_db

    def _inverse_arch(self) -> None:
        for view in self:
            self._validate_xml_encoding(view.arch)
            data = {"arch_db": view.arch}
            if "install_filename" in self.env.context:
                # we store the relative path to the resource instead of the absolute path, if found
                # (it will be missing e.g. when importing data-only modules using base_import_module)
                path_info = get_resource_from_path(self.env.context["install_filename"])
                if path_info:
                    data["arch_fs"] = "/".join(path_info[0:2])
                    data["arch_updated"] = False
            view.write(data)
            # the xml_translate will clean the arch_db when write (e.g. ('<div>') -> ('<div></div>'))
            # view.arch should be reassigned here
            view.arch = view.arch_db
        # the field 'arch' depends on the context and has been implicitly
        # modified in all languages; the invalidation below ensures that the
        # field does not keep an old value in another environment
        self.invalidate_recordset(["arch"])

    @api.depends("arch")
    @api.depends_context("read_arch_from_file")
    def _compute_arch_base(self) -> None:
        # 'arch_base' is the same as 'arch' without translation
        for view, view_wo_lang in zip(self, self.with_context(lang=None), strict=True):
            view.arch_base = view_wo_lang.arch

    def _inverse_arch_base(self) -> None:
        for view, view_wo_lang in zip(self, self.with_context(lang=None), strict=True):
            self._validate_xml_encoding(view.arch_base)
            view_wo_lang.arch = view.arch_base

    def reset_arch(self, mode: str = "soft") -> None:
        """Reset the view arch to its previous arch (soft) or its XML file arch
        if exists (hard).
        """
        for view in self:
            arch = False
            if mode == "soft":
                arch = view.arch_prev
                write_dict = {"arch_db": arch}
            elif mode == "hard" and view.arch_fs:
                arch = view.with_context(read_arch_from_file=True, lang=None).arch
                write_dict = {
                    "arch_db": arch,
                    "arch_prev": False,
                    "arch_updated": False,
                }
            if arch:
                # Don't save current arch in previous since we reset, this arch is probably broken
                view.with_context(no_save_prev=True, lang=None).write(write_dict)

    @api.depends("write_date")
    def _compute_model_data_id(self) -> None:
        # get the first ir_model_data record corresponding to self
        self.model_data_id = False
        domain = [("model", "=", "ir.ui.view"), ("res_id", "in", self.ids)]
        # Build a lookup dict to avoid per-row browse() allocations.
        view_by_id = {v.id: v for v in self}
        for data in (
            self.env["ir.model.data"]
            .sudo()
            .search_read(domain, ["res_id"], order="id desc")
        ):
            if view := view_by_id.get(data["res_id"]):
                view.model_data_id = data["id"]

    def _search_model_data_id(
        self, operator: str, value: Any
    ) -> list[tuple[str, str, Any]] | type[NotImplemented]:
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        name = "name" if isinstance(value, str) else "id"
        domain = [("model", "=", "ir.ui.view"), (name, operator, value)]
        query = self.env["ir.model.data"].sudo()._search(domain)
        return [("id", "in", query.subselect("res_id"))]

    @api.depends("model")
    def _compute_model_id(self) -> None:
        for record in self:
            record.model_id = self.env["ir.model"]._get(record.model)

    def _inverse_compute_model_id(self) -> None:
        for record in self:
            record.model = record.model_id.model

    @api.depends("arch", "inherit_id")
    def _compute_invalid_locators(self) -> None:
        def assess_locator(source: _Element, spec: _Element) -> dict[str, Any] | None:
            node = None
            with suppress(ValidationError):  # Syntax error
                # If locate_node returns None here:
                # Invalid expression: Ok Syntax, but cannot be anchored to the parent view.
                node = self.locate_node(source, spec)

            if node is None:
                return {
                    "tag": spec.tag,
                    "attrib": dict(spec.attrib),
                    "sourceline": spec.sourceline,
                }
            return None

        self.invalid_locators = False
        for view in self:
            if not view.inherit_id or not view.arch:
                continue
            try:
                # When an arch above the current one is invalid, we don't want to raise
                # instead, we want to continue using the form view.
                # This can happen when an invalid xpath has been forcibly written without checking
                # Via SQL or during the upgrade process
                source = view.with_context(
                    ir_ui_view_tree_cut_off_view=view
                )._get_combined_arch()
            except (
                ValidationError,
                ValueError,
            ):  # Xpath syntax Invalid , Xpath element unfound
                # Flagging The field as not empty and with custom information.
                # We don't do anything with the object, but the information
                # may give some clues for debugging.
                # Also, for display purposes in Form view, the field needs not be falsy.
                view.invalid_locators = [{"broken_hierarchy": True}]
                continue

            invalid_locators = []
            specs = collections.deque([etree.fromstring(view.arch)])
            while specs:
                spec = specs.popleft()
                if isinstance(spec, etree._Comment):
                    continue
                if spec.tag == "data":
                    specs.extend(spec)
                    continue

                if invalid_locator := assess_locator(source, spec):
                    invalid_locators.append(invalid_locator)
                else:
                    position, mode = spec.get("position"), spec.get("mode")
                    for sub_spec in spec:
                        sub_position = sub_spec.get("position")
                        if sub_position == "move" and (
                            position != "replace" or mode != "inner"
                        ):
                            if invalid_move := assess_locator(source, sub_spec):
                                invalid_locators.append(invalid_move)
                        elif sub_position:
                            invalid_locators.append(
                                {
                                    "tag": sub_spec.tag,
                                    "attrib": dict(sub_spec.attrib),
                                    "sourceline": sub_spec.sourceline,
                                }
                            )

                    # Since subsequent xpaths may be dependent on previous xpaths, we apply the spec.
                    # ValueError is raised for invalid: mode/attributes/position attributes,
                    # <attribute> with 'add'/'remove' containing text, or python expression separators.
                    with suppress(ValueError):
                        source = apply_inheritance_specs(source, spec)
            view.invalid_locators = invalid_locators or False

    def _compute_xml_id(self) -> None:
        xml_ids = collections.defaultdict(list)
        domain = [("model", "=", "ir.ui.view"), ("res_id", "in", self.ids)]
        for data in (
            self.env["ir.model.data"]
            .sudo()
            .search_read(domain, ["module", "name", "res_id"])
        ):
            xml_ids[data["res_id"]].append(f"{data['module']}.{data['name']}")
        for view in self:
            view.xml_id = xml_ids.get(view.id, [""])[0]

    def _valid_inheritance(self, arch: _Element) -> bool:
        """Check whether view inheritance is based on translated attribute."""
        for node in _xpath_position(arch):
            # inheritance may not use a translated attribute as selector
            if node.tag == "xpath":
                match = TRANSLATED_ATTRS_RE.search(node.get("expr", ""))
                if match:
                    message = (
                        "View inheritance may not use attribute %r as a selector."
                        % match.group(1)
                    )
                    self._raise_view_error(message, node)
                if WRONGCLASS.search(node.get("expr", "")):
                    _logger.warning(
                        "Error-prone use of @class in view %s (%s): use the "
                        "hasclass(*classes) function to filter elements by "
                        "their classes",
                        self.name,
                        self.xml_id,
                    )
            else:
                for attr in TRANSLATED_ATTRS:
                    if node.get(attr):
                        message = (
                            "View inheritance may not use attribute %r as a selector."
                            % attr
                        )
                        self._raise_view_error(message, node)
        return True

    def _check_xml(self) -> bool:
        # Sanity checks: the view should not break anything upon rendering!
        # Any exception raised below will cause a transaction rollback.
        partial_validation = self.env.context.get("ir_ui_view_partial_validation")
        views = self.with_context(
            validate_view_ids=(self._ids if partial_validation else True)
        )

        for view in views:
            if partial_validation and not view.arch:
                continue
            try:
                # verify the view is valid xml and that the inheritance resolves
                if view.inherit_id:
                    view_arch = etree.fromstring(view.arch or "<data/>")
                    view._valid_inheritance(view_arch)

                combined_arch = view._get_combined_arch()

                # check primary view that extends this current view
                # keep a way to skip this check to avoid marking too many views as failed during an upgrade
                if not self.env.context.get("_skip_primary_extensions_check") and (
                    view.inherit_id or view.inherit_children_ids
                ):
                    root = view
                    while root.inherit_id and root.mode != "primary":
                        root = root.inherit_id
                    sibling_primary_views = self.env["ir.ui.view"]
                    stack = [root]
                    while stack:
                        root = stack.pop()
                        for child in root.inherit_children_ids:
                            if child.mode == "primary":
                                sibling_primary_views += child
                            else:
                                stack.append(child)

                    # During an upgrade, we can only use the views that have been
                    # fully upgraded already.
                    if (
                        self.pool._init
                        and sibling_primary_views
                        and self.pool._init_modules
                    ):
                        query = sibling_primary_views._get_filter_xmlid_query()
                        sql = SQL(
                            query,
                            res_ids=tuple(sibling_primary_views.ids),
                            modules=tuple(self.pool._init_modules),
                        )
                        loaded_view_ids = {
                            id_ for (id_,) in self.env.execute_query(sql)
                        }
                        loaded_view_ids.update(
                            {
                                id
                                for id, xid in (
                                    sibling_primary_views
                                    - views.browse(loaded_view_ids)
                                )
                                .get_external_id()
                                .items()
                                if xid in self.pool.loaded_xmlids
                            }
                        )
                        sibling_primary_views = sibling_primary_views.browse(
                            loaded_view_ids
                        )

                    # Check if we know how to apply inheritances
                    sibling_primary_views._get_combined_archs()

                if view.type == "qweb":
                    continue
            except (etree.ParseError, ValueError) as e:
                err = ValidationError(
                    _(
                        "Error while parsing or validating view (%(view)s):\n\n%(error)s",
                        error=e,
                        view=view.key or view.id,
                    )
                ).with_traceback(e.__traceback__)
                err.context = getattr(e, "context", None)
                raise err from None

            try:
                # verify that all fields used are valid, etc.
                view._validate_view(combined_arch, view.model)
                combined_archs = [combined_arch]

                if _xpath_attrs(combined_arch) or _xpath_states(combined_arch):
                    view_name = (
                        f"{view.name} ({view.xml_id})" if view.xml_id else view.name
                    )
                    err = ValidationError(
                        _(
                            'Since 17.0, the "attrs" and "states" attributes are no longer used.\nView: %(name)s in %(file)s',
                            name=view_name,
                            file=view.arch_fs,
                        )
                    )
                    err.context = {"name": "invalid view"}
                    raise err

                if combined_archs[0].tag == "data":
                    # A <data> element is a wrapper for multiple root nodes
                    combined_archs = combined_archs[0]
                for view_arch in combined_archs:
                    for node in _xpath_validate(view_arch):
                        del node.attrib["__validate__"]
                    check = valid_view(view_arch, env=self.env, model=view.model)
                    if not check:
                        view_name = (
                            f"{view.name} ({view.xml_id})" if view.xml_id else view.name
                        )
                        raise ValidationError(
                            _(
                                "Invalid view %(name)s definition in %(file)s",
                                name=view_name,
                                file=view.arch_fs,
                            )
                        )
            except ValueError as e:
                if hasattr(e, "context"):
                    lines = etree.tostring(
                        combined_arch, encoding="unicode"
                    ).splitlines(keepends=True)
                    fivelines = "".join(
                        lines[max(0, e.context["line"] - 3) : e.context["line"] + 2]
                    )
                    err = ValidationError(
                        _(
                            "Error while validating view near:\n\n%(fivelines)s\n%(error)s",
                            fivelines=fivelines,
                            error=e,
                        )
                    )
                    err.context = e.context
                    raise err.with_traceback(e.__traceback__) from None
                if e.__context__:
                    err = ValidationError(
                        _(
                            "Error while validating view (%(view)s):\n\n%(error)s",
                            view=view.key or view.id,
                            error=e.__context__,
                        )
                    )
                    err.context = {"name": "invalid view"}
                    raise err.with_traceback(e.__context__.__traceback__) from None
                raise ValidationError(
                    _(
                        "Error while validating view (%(view)s):\n\n%(error)s",
                        view=view.key or view.id,
                        error=e,
                    )
                )

        return True

    @api.constrains("group_ids", "inherit_id", "mode")
    def _check_groups(self) -> None:
        for view in self:
            if view.group_ids and view.inherit_id and view.mode != "primary":
                raise ValidationError(
                    _(
                        "Inherited view cannot have 'Groups' define on the record. Use 'groups' attributes inside the view definition"
                    )
                )

    @api.constrains("inherit_id")
    def _check_000_inheritance(self) -> None:
        # NOTE: constraints methods are check alphabetically. Always ensure this method will be
        #       called before other constraint methods to avoid infinite loop in `_get_combined_arch`.
        if self._has_cycle("inherit_id"):
            raise ValidationError(_("You cannot create recursive inherited views."))

    _inheritance_mode = models.Constraint(
        "CHECK (mode != 'extension' OR inherit_id IS NOT NULL)",
        "Invalid inheritance mode: if the mode is 'extension', the view must extend an other view",
    )
    _qweb_required_key = models.Constraint(
        "CHECK (type != 'qweb' OR key IS NOT NULL)",
        "Invalid key: QWeb view should have a key",
    )
    _model_type_inherit_id = models.Index("(model, inherit_id)")

    def _compute_defaults(self, values: dict[str, Any]) -> dict[str, Any]:
        if "inherit_id" in values:
            # Do not automatically change the mode if the view already has an inherit_id,
            # and the user change it to another.
            if not values["inherit_id"] or all(not view.inherit_id for view in self):
                values.setdefault(
                    "mode", "extension" if values["inherit_id"] else "primary"
                )
        return values

    @api.depends("arch")
    def _compute_warning_info(self) -> None:
        for view in self:
            view.warning_info = ""
            if not view.arch:
                continue
            try:
                if view.inherit_id:
                    view_arch = etree.fromstring(view.arch)
                    view._valid_inheritance(view_arch)
                combined_arch = view._get_combined_arch()
                if view.type != "qweb":
                    view._postprocess_view(
                        combined_arch, view.model, is_compute_warning_info=True
                    )
            except (etree.ParseError, ValueError) as e:
                view.warning_info = str(e)

    def _validate_xml_encoding(self, text: str | None) -> None:
        if isinstance(text, str) and re.search(
            r"<\?xml[^>]*encoding=.*?\?>", text, re.IGNORECASE
        ):
            raise UserError(
                _(
                    "Unicode strings with encoding declaration are not supported in XML.\n"
                    "Remove the encoding declaration."
                )
            )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        valid_types = self._fields["type"]._selection
        # Prefetch parent view types in batch to avoid N+1 queries
        inherit_ids = {
            v["inherit_id"]
            for v in vals_list
            if v.get("inherit_id") and not v.get("type")
        }
        parent_types = {}
        if inherit_ids:
            parents = self.browse(inherit_ids)
            parent_types = {p.id: p.type for p in parents}

        for values in vals_list:
            if "arch_db" in values and not values["arch_db"]:
                # delete empty arch_db to avoid triggering _check_xml before _inverse_arch_base is called
                del values["arch_db"]

            if not values.get("type"):
                if values.get("inherit_id"):
                    values["type"] = parent_types.get(values["inherit_id"])
                else:
                    try:
                        if not values.get("arch") and not values.get("arch_base"):
                            raise ValidationError(_("Missing view architecture."))
                        values["type"] = etree.fromstring(
                            values.get("arch") or values.get("arch_base")
                        ).tag
                        if values["type"] not in valid_types:
                            raise ValidationError(
                                _(
                                    "Invalid view type: '%(view_type)s'.\n"
                                    "You might have used an invalid starting tag in the architecture.\n"
                                    "Allowed types are: %(valid_types)s",
                                    view_type=values["type"],
                                    valid_types=", ".join(valid_types),
                                )
                            )
                    except etree.ParseError, ValueError:
                        # don't raise here, the constraint that runs `self._check_xml` will
                        # do the job properly.
                        pass
            if not values.get("key") and values.get("type") == "qweb":
                values["key"] = f"gen_key.{str(uuid.uuid4())[:6]}"
            if not values.get("name"):
                values["name"] = f"{values.get('model')} {values['type']}"
            # Create might be called with either `arch` (xml files), `arch_base` (form view) or `arch_db`.
            values["arch_prev"] = (
                values.get("arch_base") or values.get("arch_db") or values.get("arch")
            )
            # write on arch: bypass _inverse_arch()
            if "arch" in values:
                values["arch_db"] = values.pop("arch")
                if "install_filename" in self.env.context:
                    # we store the relative path to the resource instead of the absolute path, if found
                    # (it will be missing e.g. when importing data-only modules using base_import_module)
                    path_info = get_resource_from_path(
                        self.env.context["install_filename"]
                    )
                    if path_info:
                        values["arch_fs"] = "/".join(path_info[0:2])
                        values["arch_updated"] = False
            values.update(self._compute_defaults(values))

        self.env.registry.clear_cache("templates")
        result = super().create(vals_list)
        result.with_context(ir_ui_view_partial_validation=True)._check_xml()
        return result

    def write(self, vals: dict[str, Any]) -> bool:
        # Keep track if view was modified. That will be useful for the --dev mode
        # to prefer modified arch over file arch.
        if (
            "arch_updated" not in vals
            and ("arch" in vals or "arch_base" in vals)
            and "install_filename" not in self.env.context
        ):
            vals["arch_updated"] = True

        # drop the corresponding view customizations (used for dashboards for example), otherwise
        # not all users would see the updated views
        custom_view = (
            self.env["ir.ui.view.custom"].sudo().search([("ref_id", "in", self.ids)])
        )
        if custom_view:
            custom_view.unlink()

        self.env.registry.clear_cache("templates")
        if "arch_db" in vals and not self.env.context.get("no_save_prev"):
            for view in self:
                super(type(self), view).write({"arch_prev": view.arch_db})

        res = super().write(self._compute_defaults(vals))

        # Check the xml of the view if it gets re-activated or changed.
        if "active" in vals or "arch_db" in vals or "inherit_id" in vals:
            self._check_xml()

        return res

    def unlink(self) -> bool:
        # if in uninstall mode and has children views, emulate an ondelete cascade
        if self.env.context.get("_force_unlink", False) and self.inherit_children_ids:
            self.inherit_children_ids.unlink()
        self.env.registry.clear_cache("templates")
        return super().unlink()

    def _update_field_translations(
        self,
        field_name: str,
        translations: dict[str, str | typing.Literal[False] | dict[str, str]],
        digest: Callable[[str], str] | None = None,
        source_lang: str = "",
    ) -> bool:
        return super(
            IrUiView, self.with_context(no_save_prev=True)
        )._update_field_translations(
            field_name, translations, digest=digest, source_lang=source_lang
        )

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        has_default_without_key = default and "key" not in default
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for view, vals in zip(self, vals_list, strict=True):
            if view.key and has_default_without_key:
                vals["key"] = default.get("key", f"{view.key}_{str(uuid.uuid4())[:6]}")
        return vals_list

    # default view selection
    @api.model
    def default_view(self, model: str, view_type: str) -> int | bool:
        """Fetches the default view for the provided (model, view_type) pair:
         primary view with the lowest priority.

        :param str model:
        :param str view_type:
        :return: id of the default view of False if none found
        :rtype: int | bool
        """
        return self.search(self._get_default_view_domain(model, view_type), limit=1).id

    @api.model
    def _get_default_view_domain(self, model: str, view_type: str) -> Domain:
        return Domain(
            [
                ("model", "=", model),
                ("type", "=", view_type),
                ("mode", "=", "primary"),
            ]
        )

    # ------------------------------------------------------
    # Inheritance mecanism
    # ------------------------------------------------------
    @api.model
    def _get_inheriting_views_domain(self) -> Domain:
        """Return a domain to filter the sub-views to inherit from."""
        tree_cut_off_view = self.env.context.get("ir_ui_view_tree_cut_off_view")
        domain = Domain("active", "=", True)
        if tree_cut_off_view:
            return domain | Domain("id", "=", tree_cut_off_view.id)
        return domain

    @api.model
    def _get_filter_xmlid_query(self) -> str:
        """This method is meant to be overridden by other modules."""
        return """SELECT res_id FROM ir_model_data
                  WHERE res_id IN %(res_ids)s AND model = 'ir.ui.view' AND module IN %(modules)s
               """

    def _get_inheriting_views(self) -> Self:
        """
        Determine the views that inherit from the current recordset, and return
        them as a recordset, ordered by priority then by id.
        """
        if not self.ids:
            return self.browse()
        domain = self._get_inheriting_views_domain()
        query = self._search(domain)
        where_clause = query.where_clause
        assert query.from_clause == SQL.identifier(
            "ir_ui_view"
        ), f"Unexpected from clause: {query.from_clause}"

        field_names = [
            f.name for f in self._fields.values() if f.prefetch is True and not f.groups
        ]
        aliased_names = SQL(", ").join(
            SQL(
                "%s AS %s",
                self._field_to_sql("ir_ui_view", name),
                SQL.identifier(name),
            )
            for name in field_names
        )

        query = SQL(
            """
            WITH RECURSIVE ir_ui_view_inherits AS (
                SELECT ir_ui_view.id, %(aliased_names)s
                FROM ir_ui_view
                WHERE id IN %(ids)s AND (%(where_clause)s)
            UNION
                SELECT ir_ui_view.id, %(aliased_names)s
                FROM ir_ui_view
                INNER JOIN ir_ui_view_inherits parent ON parent.id = ir_ui_view.inherit_id
                WHERE coalesce(ir_ui_view.model, '') = coalesce(parent.model, '')
                      AND ir_ui_view.mode = 'extension'
                      AND (%(where_clause)s)
            )
            SELECT
                v.id, %(field_names)s
            FROM ir_ui_view_inherits as v
            ORDER BY v.priority, v.id
        """,
            aliased_names=aliased_names,
            field_names=SQL(", ").join(SQL.identifier("v", f) for f in field_names),
            ids=tuple(self.ids),
            where_clause=where_clause,
        )
        # ORDER BY v.priority, v.id:
        # 1/ sort by priority: abritrary value set by developers on some
        #    views to solve "dependency hell" problems and force a view
        #    to be combined earlier or later. e.g. all views created via
        #    studio have a priority=99 to be loaded last.
        # 2/ sort by view id: the order the views were inserted in the
        #    database. e.g. base views are placed before stock ones.

        rows = self.env.execute_query(query)
        if not rows:
            return self.browse()

        ids, *columns = zip(*rows, strict=False)
        views = self.browse(ids)

        # optimization: fill in cache of retrieved fields
        for fname, column in zip(field_names, columns, strict=True):
            self._fields[fname]._insert_cache(views, column)

        return views

    def _filter_loaded_views(self, check_view_ids: set[int]) -> Self:
        """
        During the module upgrade phase it may happen that a view is
        present in the database but the fields it relies on are not
        fully loaded yet. This method only considers views that belong
        to modules whose code is already loaded. Custom views defined
        directly in the database are loaded only after the module
        initialization phase is completely finished.
        """
        # check that all found ids have a corresponding xml_id in a loaded module
        ids_to_check = [vid for vid in self.ids if vid not in check_view_ids]
        if not ids_to_check:
            return self
        install_module = self.env.context.get("install_module")
        loaded_modules = tuple(self.pool._init_modules)
        if install_module:
            loaded_modules += (install_module,)
        query = self._get_filter_xmlid_query()
        sql = SQL(query, res_ids=tuple(ids_to_check), modules=loaded_modules)
        valid_view_ids = {
            id_ for (id_,) in self.env.execute_query(sql)
        } | check_view_ids
        return self.browse(vid for vid in self.ids if vid in valid_view_ids)

    def _check_view_access(self) -> bool:
        """Verify that a view is accessible by the current user based on the
        groups attribute. Views with no groups are considered private.
        """
        if self.inherit_id and self.mode != "primary":
            return self.inherit_id._check_view_access()
        if set(self.group_ids.ids) & set(self.env.user._get_group_ids()):
            return True
        if self.group_ids:
            error = _(
                "View '%(name)s' accessible only to groups %(groups)s ",
                name=self.key,
                groups=", ".join([g.name for g in self.group_ids]),
            )
        else:
            error = _("View '%(name)s' is private", name=self.key)
        raise AccessError(error)

    def _raise_view_error(
        self,
        message: str,
        node: _Element | None = None,
        *,
        from_exception: BaseException | None = None,
        from_traceback: Any = None,
    ) -> None:
        """Handle a view error by raising an exception.

        :param str message: message to raise or log, augmented with contextual
                            view information
        :param node: the lxml element where the error is located (if any)
        :param BaseException | None from_exception:
            when raising an exception, chain it to the provided one (default:
            disable chaining)
        :param Any from_traceback:
            when raising an exception, start with this traceback (default: start
            at exception creation)
        """
        err = ValueError(message).with_traceback(from_traceback)
        err.context = {
            "view": self,
            "name": getattr(self, "name", None),
            "xmlid": self.env.context.get("install_xmlid") or self.xml_id,
            "view.model": self.model,
            "view.parent": self.inherit_id,
            "file": self.env.context.get("install_filename"),
            "line": node.sourceline if node is not None else 1,
        }
        raise err from from_exception

    def _log_view_warning(self, message: str, node: _Element) -> None:
        """Handle a view issue by logging a warning.

        :param str message: message to raise or log, augmented with contextual
                            view information
        :param node: the lxml element where the error is located (if any)
        """
        error_context = {
            "view": self,
            "name": getattr(self, "name", None),
            "xmlid": self.env.context.get("install_xmlid") or self.xml_id,
            "view.model": self.model,
            "view.parent": self.inherit_id,
            "file": self.env.context.get("install_filename"),
            "line": node.sourceline if node is not None else 1,
        }
        _logger.warning(
            "%s\nView error context:\n%s",
            message,
            pprint.pformat(error_context),
        )

    def locate_node(self, arch: _Element, spec: _Element) -> _Element | None:
        """Locate a node in a source (parent) architecture.

        Given a complete source (parent) architecture (i.e. the field
        `arch` in a view), and a 'spec' node (a node in an inheriting
        view that specifies the location in the source view of what
        should be changed), return (if it exists) the node in the
        source view matching the specification.

        :param arch: a parent architecture to modify
        :param spec: a modifying node in an inheriting view
        :return: a node in the source matching the spec
        """
        return locate_node(arch, spec)

    def inherit_branding(self, specs_tree: _Element) -> _Element:
        for node in specs_tree.iterchildren(tag=etree.Element):
            xpath = node.getroottree().getpath(node)
            if node.tag in {"data", "xpath"} or node.get("position"):
                self.inherit_branding(node)
            elif node.get("t-field"):
                node.set("data-oe-xpath", xpath)
                self.inherit_branding(node)
            else:
                node.set("data-oe-id", str(self.id))
                node.set("data-oe-xpath", xpath)
                node.set("data-oe-model", "ir.ui.view")
                node.set("data-oe-field", "arch")
        return specs_tree

    def _add_validation_flag(
        self,
        combined_arch: _Element,
        view: Self | None = None,
        arch: _Element | None = None,
    ) -> None:
        """Add a validation flag on elements in ``combined_arch`` or ``arch``.
        This is part of the partial validation of views.

        :param _Element combined_arch: the architecture to be modified by ``arch``
        :param view: an optional view inheriting ``self``
        :param _Element | None arch: an optional modifying architecture from inheriting
            view ``view``
        """
        # validate_view_ids is either falsy (no validation), True (full
        # validation) or a collection of ids (partial validation)
        validate_view_ids = self.env.context.get("validate_view_ids")
        if not validate_view_ids:
            return

        if validate_view_ids is True or self.id in validate_view_ids:
            # optimization, flag the root node
            combined_arch.set("__validate__", "1")
            return

        if view is None or view.id not in validate_view_ids:
            return

        for node in _xpath_position(arch):
            if node.get("position") in ("after", "before", "inside"):
                # validate the elements being inserted, except the ones that
                # specify a move, as in:
                #   <field name="foo" position="after">
                #       <field name="bar" position="move"/>
                #   </field>
                for child in node.iterchildren(tag=etree.Element):
                    if not child.get("position"):
                        child.set("__validate__", "1")
            if node.get("position") == "replace":
                # validate everything, since this impacts the whole arch
                combined_arch.set("__validate__", "1")
                break
            if node.get("position") == "attributes":
                # validate the element being modified by adding
                # attribute "__validate__" on it:
                #   <field name="foo" position="attributes">
                #       <attribute name="readonly">1</attribute>
                #       <attribute name="__validate__">1</attribute>    <!-- add this -->
                #   </field>
                node.append(E.attribute("1", name="__validate__"))

    @api.model
    def apply_inheritance_specs(
        self, source: _Element, specs_tree: _Element, pre_locate: Any = None
    ) -> _Element:
        """Apply an inheriting view (a descendant of the base view)

        Apply to a source architecture all the spec nodes (i.e. nodes
        describing where and what changes to apply to some parent
        architecture) given by an inheriting view.

        :param _Element source: a parent architecture to modify
        :param _Element specs_tree: a modifying architecture in an inheriting view
        :param Any pre_locate: optional function executed before locating a node.
                               Receives an arch as argument.
        :return: a modified source where the specs are applied
        :rtype: _Element
        """
        # Queue of specification nodes (i.e. nodes describing where and
        # changes to apply to some parent architecture).
        try:
            source = apply_inheritance_specs(
                source,
                specs_tree,
                inherit_branding=self.env.context.get("inherit_branding"),
                pre_locate=pre_locate,
            )
        except ValueError as e:
            self._raise_view_error(str(e), specs_tree)
        return source

    def _combine(self, hierarchy: dict[Self, list[Self]]) -> _Element:
        """
        Return self's arch combined with its inherited views archs.

        :param hierarchy: mapping from parent views to their child views
        :return: combined architecture
        :rtype: _Element
        """
        self.ensure_one()
        if self.mode != "primary":
            raise ValueError(
                f"_combine() requires a primary view, got mode={self.mode!r}"
            )

        # We achieve a pre-order depth-first hierarchy traversal where
        # primary views (and their children) are traversed after all the
        # extensions for the current primary view have been visited.
        #
        # https://en.wikipedia.org/wiki/Tree_traversal#Depth-first_search_of_binary_tree
        #
        # Example:                  hierarchy = {
        #                               1: [2, 3],  # primary view
        #             1*                2: [4, 5],
        #            / \                3: [],
        #           2   3               4: [6],     # primary view
        #          / \                  5: [7, 8],
        #         4*  5                 6: [],
        #        /   / \                7: [],
        #       6   7   8               8: [],
        #                           }  # noqa: ERA001, RUF100
        #
        # Tree traversal order (`view` and `queue` at the `while` stmt):
        #   1 [2, 3]  # noqa: ERA001
        #   2 [5, 3, 4]  # noqa: ERA001
        #   5 [7, 8, 3, 4]  # noqa: ERA001
        #   7 [8, 3, 4]  # noqa: ERA001
        #   8 [3, 4]  # noqa: ERA001
        #   3 [4]  # noqa: ERA001
        #   4 [6]  # noqa: ERA001
        #   6 []
        combined_arch = etree.fromstring(self.arch)
        if self.env.context.get("inherit_branding"):
            combined_arch.attrib.update(
                {
                    "data-oe-model": "ir.ui.view",
                    "data-oe-id": str(self.id),
                    "data-oe-field": "arch",
                }
            )
        self._add_validation_flag(combined_arch)

        # The depth-first traversal is implemented with a double-ended queue.
        # The queue is traversed from left to right, and after each view in the
        # queue is processed, its children are pushed at the left of the queue,
        # so that they are traversed in order.  The queue is therefore mostly
        # used as a stack.  An exception is made for primary views, which are
        # pushed at the other end of the queue, so that they are applied after
        # all extensions have been applied.
        queue = collections.deque(sorted(hierarchy[self], key=lambda v: v.mode))
        tree_cut_off_view = self.env.context.get("ir_ui_view_tree_cut_off_view")
        while queue:
            view = queue.popleft()
            if view == tree_cut_off_view:
                break
            arch = etree.fromstring(view.arch or "<data/>")
            if view.env.context.get("inherit_branding"):
                view.inherit_branding(arch)
            self._add_validation_flag(combined_arch, view, arch)
            combined_arch = view.apply_inheritance_specs(combined_arch, arch)

            for child_view in reversed(hierarchy[view]):
                if child_view.mode == "primary":
                    queue.append(child_view)
                else:
                    queue.appendleft(child_view)

        return combined_arch

    def get_combined_arch(self) -> str:
        """Return the arch of ``self`` (as a string) combined with its inherited views."""
        return etree.tostring(self._get_combined_arch(), encoding="unicode")

    def _get_combined_arch(self) -> _Element:
        self.ensure_one()
        return self._get_combined_archs()[0]

    def _get_combined_archs(self) -> list[_Element]:
        """Return the arch of ``self`` (as an etree) combined with its inherited views."""
        parented = []
        roots = self.env["ir.ui.view"]
        for root in self:
            parented.append(view_ids := [])
            while True:
                view_ids.append(root.id)
                if not root.inherit_id:
                    roots += root
                    break
                root = root.inherit_id
        views = self.env["ir.ui.view"].browse(
            unique(view_id for view_ids in parented for view_id in view_ids)
        )

        # Add inherited views to the list of loading forced views
        # Otherwise, inherited views could not find elements created in
        # their direct parents if that parent is defined in the same module
        # introduce check_view_ids in context
        if "check_view_ids" not in views.env.context:
            views = views.with_context(check_view_ids=[])
        views.env.context["check_view_ids"].extend(views.ids)

        # Map each node to its children nodes. Note that all children nodes are
        # part of a single prefetch set, which is all views to combine.
        all_tree_views = views._get_inheriting_views()

        # During an upgrade, we can only use the views that have been
        # fully upgraded already.
        if self.pool._init and not self.env.context.get("load_all_views"):
            all_tree_views = all_tree_views._filter_loaded_views(
                set(views.env.context["check_view_ids"])
            )

        # get the global children views then get hierarchy for each views
        children_views = collections.defaultdict(list)
        for view in all_tree_views:
            children_views[view.inherit_id].append(view)

        def get_hierarchy(
            root: Self,
            parented_ids: list[int],
            _hierarchy: dict[Self, list[Self]] | None = None,
        ) -> dict[Self, list[Self]]:
            if _hierarchy is None:
                _hierarchy = collections.defaultdict(list)
            _hierarchy[root.inherit_id].append(root)
            for child in children_views[root]:
                if child.id in parented_ids or child.mode != "primary":
                    get_hierarchy(child, parented_ids, _hierarchy)
            return _hierarchy

        roots = roots.with_prefetch(all_tree_views._prefetch_ids)

        return [
            root._combine(get_hierarchy(root, parented_ids))
            for root, parented_ids in zip(roots, parented, strict=False)
        ]

    def _get_view_refs(self, node: _Element) -> dict[str, str]:
        """Extract the `[view_type]_view_ref` keys and values from the node context attribute,
        giving the views to use for a field node.

        :param node: the field node as an etree
        :return: a dictonary mapping the `[view_type]_view_ref` key to the xmlid of the view to use for that view type.
        """
        if not node.get("context"):
            return {}
        return {
            m.group("view_type"): m.group("view_id")
            for m in ref_re.finditer(node.get("context"))
        }

    # ------------------------------------------------------
    # Get views and cache
    # ------------------------------------------------------

    @api.model
    def _get_cached_template_prefetched_keys(self) -> list[str]:
        return ["id", "key", "active"]

    def _get_template_minimal_cache_keys(self) -> tuple[bool]:
        return (bool(self.env.context.get("active_test", True)),)

    @api.model
    @tools.ormcache(
        "id_or_xmlid",
        "isinstance(id_or_xmlid, str) and self._get_template_minimal_cache_keys()",
        cache="templates",
    )
    def _get_cached_template_info(
        self, id_or_xmlid: int | str, _view: Self | None = None
    ) -> dict[str, Any]:
        """Return the ir.ui.view id from the xml id, use `_preload_views`."""
        view = None
        error = False
        if _view is not None:
            view = _view
        elif isinstance(id_or_xmlid, int):
            view = self.env["ir.ui.view"].sudo().browse(id_or_xmlid)
            try:
                _ = view.key
            except MissingError:
                view = None
                error = MissingError(
                    self.env._("Template not found: '%s'", id_or_xmlid)
                )
            except UserError as e:
                view = None
                error = e
        else:
            preload = self.sudo()._preload_views([id_or_xmlid])
            if id_or_xmlid in preload:
                info = preload[id_or_xmlid]
                view = info["view"]
                error = info["error"]
            else:
                error = SyntaxError("Error compiling template")
        info = {
            f: view[f] if view else None
            for f in self._get_cached_template_prefetched_keys()
        }
        info["error"] = error
        return info

    @api.model
    def _get_template_view(
        self, id_or_xmlid: int | str, raise_if_not_found: bool = True
    ) -> Self:
        info = self._get_cached_template_info(id_or_xmlid)
        if info["error"] and raise_if_not_found:
            raise info["error"]
        return self.env["ir.ui.view"].browse(info["id"])

    @api.model
    def _get_template_domain(self, xmlids: list[str]) -> Domain:
        return Domain("key", "in", xmlids)

    @api.model
    def _get_template_order(self) -> str:
        return "priority, id"

    @api.model
    def _fetch_template_views(
        self, ids_or_xmlids: Sequence[int | str]
    ) -> dict[int | str, Self | Exception]:
        """Return the view corresponding to ``template``, which may be a
        view ID or an XML ID. Note that this method may be overridden for other
        kinds of template values.
        """
        IrUiView = (
            self.env["ir.ui.view"]
            .sudo()
            .with_context(load_all_views=True, raise_if_not_found=True)
        )

        ids, xmlids = partition(lambda v: isinstance(v, int), ids_or_xmlids)

        # search view in ir.ui.view
        view_by_id = {}
        field_names = [f.name for f in IrUiView._fields.values() if f.prefetch is True]
        if xmlids:
            domain = Domain("id", "in", ids) | Domain(self._get_template_domain(xmlids))
            views = IrUiView.search_fetch(
                domain, field_names, order=self._get_template_order()
            )
        else:
            views = IrUiView.browse(ids)

        for view in views:
            try:
                if view.key in view_by_id:
                    # keeps views according to their priority order
                    continue
            except MissingError:
                continue
            view_by_id[view.id] = view
            if view.key:
                view_by_id[view.key] = view

        # search missing view from xmlid in ir.model.data
        missing_xmlid_views = [
            xmlid for xmlid in xmlids if "." in xmlid and xmlid not in view_by_id
        ]
        if missing_xmlid_views:
            domain = Domain.OR(
                Domain("model", "=", "ir.ui.view")
                & Domain("module", "=", res[0])
                & Domain("name", "=", res[1])
                for xmlid in missing_xmlid_views
                if (res := xmlid.split(".", 1))
            )

            model_data_records = self.env["ir.model.data"].sudo().search(domain)
            all_views = IrUiView.browse(model_data_records.mapped("res_id")).exists()
            existing_ids = set(all_views._ids)
            view_map = {v.id: v for v in all_views}
            for model_data in model_data_records:
                if model_data.res_id in existing_ids:
                    view = view_map[model_data.res_id]
                    view_by_id[view.id] = view
                    xmlid = f"{model_data.module}.{model_data.name}"
                    view_by_id[xmlid] = view
                    if view.key:
                        view_by_id[view.key] = view

        for key, view in view_by_id.items():
            # push information in cache
            self._get_cached_template_info(key, _view=view)

        # create data and errors
        for view_id in ids:
            if view_id not in view_by_id:
                # push information in cache
                self._get_cached_template_info(view_id, _view=False)
                view_by_id[view_id] = MissingError(
                    self.env._(
                        "Template does not exist or has been deleted: %s",
                        view_id,
                    )
                )
        for xmlid in xmlids:
            if xmlid not in view_by_id:
                # push information in cache
                self._get_cached_template_info(xmlid, _view=False)
                view_by_id[xmlid] = MissingError(
                    self.env._("Template not found: '%s'", xmlid)
                )
        return view_by_id

    @tools.ormcache(cache="templates")
    def _clear_preload_views_cache_if_needed(self) -> None:
        """Invalidate the local cache when the orm cache is cleared"""
        self.env.cr.cache.pop("_compile_batch_", None)

    def _preload_views(
        self, refs: Sequence[int | str]
    ) -> dict[int | str, dict[str, Any]]:
        """
        Return self's arch combined with its inherited views archs.

        :param refs: list of id or xmlid
        :return: dictionary of preloaded information {id or xmlid: {xmlid, ref, view, error}}
        """
        self._clear_preload_views_cache_if_needed()

        context = {
            k: self.env.context.get(k)
            for k in self.env["ir.qweb"]._get_template_cache_keys()
        }
        cache_key = tuple(context.values())

        compile_batch = self.env.cr.cache.setdefault("_compile_batch_", {}).setdefault(
            cache_key, {}
        )

        refs = [
            int(ref) if isinstance(ref, int) or ref.isdigit() else ref for ref in refs
        ]
        missing_refs = [ref for ref in refs if ref and ref not in compile_batch]
        if not missing_refs:
            return compile_batch

        unknown_views = self._fetch_template_views(missing_refs)

        # add in cache
        for id_or_xmlid, view in unknown_views.items():
            if isinstance(view, models.BaseModel):
                compile_batch[view.id] = compile_batch[id_or_xmlid] = {
                    "xmlid": view.key or id_or_xmlid,
                    "ref": view.id,
                    "view": view,
                    "error": False,
                }
            else:
                compile_batch[id_or_xmlid] = {
                    "xmlid": id_or_xmlid,
                    "view": None,
                    "ref": None,
                    "error": view,  # MissingError
                }

        return compile_batch

    # ------------------------------------------------------
    # Postprocessing: translation, groups and modifiers
    # ------------------------------------------------------
    # TODO: remove group processing from ir_qweb
    # ------------------------------------------------------
    def postprocess_and_fields(
        self, node: _Element, model: str | None = None, **options: Any
    ) -> tuple[str, dict[str, set[str]]]:
        """Return an architecture and a description of all the fields.

        The field description combines the result of fields_get() and
        postprocess().

        :param self: the view to postprocess
        :param node: the architecture as an etree
        :param model: the view's reference model name
        :return: a tuple (arch, fields) where arch is the given node as a
            string and fields is the description of all the fields.

        """
        self and self.ensure_one()  # self is at most one view

        name_manager = self._postprocess_view(node, model or self.model, **options)
        arch = etree.tostring(node, encoding="unicode").replace("\t", "")

        models = {}
        name_managers = [name_manager]
        for name_manager in name_managers:
            models.setdefault(name_manager.model._name, set()).update(
                name_manager.available_fields
            )
            name_managers.extend(name_manager.children)

        return arch, models

    def _postprocess_access_rights(self, tree: _Element) -> _Element:
        """
        Apply group restrictions: elements with a 'groups' attribute should
        be removed from the view to people who are not members.

        Compute and set on node access rights based on view type. Specific
        views can add additional specific rights like creating columns for
        many2one-based grouping views.
        """
        group_definitions = self.env["res.groups"]._get_group_definitions()

        user_group_ids = self.env.user._get_group_ids()

        # check the read/visibility access
        @functools.cache
        def has_access(groups_key: str) -> bool:
            groups = group_definitions.from_key(groups_key)
            return groups.matches(user_group_ids)

        # check the read/visibility access
        for node in _xpath_groups_key(tree):
            if not has_access(node.attrib.pop("__groups_key__")):
                tail = node.tail
                parent = node.getparent()
                previous = node.getprevious()
                parent.remove(node)
                if tail:
                    if previous is not None:
                        previous.tail = (previous.tail or "") + tail
                    elif parent is not None:
                        parent.text = (parent.text or "") + tail
            elif node.tag == "t" and not node.attrib:
                # Move content of <t groups=""> blocks
                # and remove the <t> node.
                # This is to keep the structure
                # <group>
                #   <field name="foo"/>
                #   <field name="bar"/>
                # <group>
                # so the web client adds the label as expected.
                # This is also to avoid having <t> nodes in list views
                # e.g.
                # <list>
                #   <field name="foo"/>
                #   <t groups="foo">
                #     <field name="bar" groups="bar"/>
                #   </t>
                # </list>
                for child in reversed(node):
                    node.addnext(child)
                node.getparent().remove(node)

        # check the create and write access
        for node in _xpath_model_access(tree):
            model = self.env[node.attrib.pop("model_access_rights")]
            if node.tag == "field":
                can_create = model.has_access("create")
                can_write = model.has_access("write")
                node.set("can_create", str(bool(can_create)))
                node.set("can_write", str(bool(can_write)))
            else:
                for action, operation in (
                    ("create", "create"),
                    ("delete", "unlink"),
                    ("edit", "write"),
                ):
                    if not node.get(action) and not model.has_access(operation):
                        node.set(action, "False")
                if node.tag == "kanban":
                    group_by_name = node.get("default_group_by")
                    group_by_field = model._fields.get(group_by_name)
                    if group_by_field and group_by_field.type == "many2one":
                        group_by_model = model.env[group_by_field.comodel_name]
                        for action, operation in (
                            ("group_create", "create"),
                            ("group_delete", "unlink"),
                            ("group_edit", "write"),
                        ):
                            if not node.get(action) and not group_by_model.has_access(
                                operation
                            ):
                                node.set(action, "False")

        return tree

    def _postprocess_debug_to_cache(self, tree: _Element) -> None:
        """Transform ``groups`` containing ``base.group_no_one`` into the
        ``__debug__`` attribute for special debug-mode handling.

        ``base.group_no_one`` is not a security group but a display feature
        that controls debug-mode visibility. This method handles both the
        positive (``base.group_no_one`` → show in debug) and negated
        (``!base.group_no_one`` → hide in debug) forms, stripping them
        from the ``groups`` attribute so that ``_postprocess_access_rights``
        does not interfere with the debug-mode logic.

        Typically the templates do not match the intent when attribute 'groups'
        contains 'base.group_no_one' and other groups. In every case we could
        spot, we want an "and" and not an "or" for the condition on groups::

            <filter name="not_secured" string="Not Secured" ... groups="account.group_account_secured,base.group_no_one"/>
            or
            <menuitem ... name="Configuration" ... groups="base.group_system,base.group_no_one"/>
        """
        for node in _xpath_groups(tree):
            groups = node.attrib.get("groups", "").split(",")
            if "base.group_no_one" in groups:
                node.attrib["__debug__"] = "True"
                node.attrib["groups"] = ",".join(
                    group for group in groups if group != "base.group_no_one"
                )
            elif "!base.group_no_one" in groups:
                node.attrib["__debug__"] = "False"
                node.attrib["groups"] = ",".join(
                    group for group in groups if group != "!base.group_no_one"
                )

    def _postprocess_debug(self, tree: _Element) -> _Element:
        """Apply debug mode by making nodes invisible."""
        is_debug = self.env.user.has_group("base.group_no_one")
        for node in _xpath_debug(tree):
            debug = node.attrib.pop("__debug__") == "True"
            if debug != is_debug:
                node.attrib["invisible"] = "1"
                node.attrib["column_invisible"] = "1"
        return tree

    def _postprocess_view(
        self,
        node: _Element,
        model_name: str,
        editable: bool = True,
        node_info: dict[str, Any] | None = None,
        **options: Any,
    ) -> NameManager:
        """Process the given architecture, modifying it in-place to add and
        remove stuff.

        :param self: the optional view to postprocess
        :param node: the combined architecture as an etree
        :param model_name: the view's reference model name
        :param editable: whether the view is considered editable
        :return: the processed architecture's NameManager
        """
        root = node

        if model_name not in self.env:
            self._raise_view_error(
                _("Model not found: %(model)s", model=model_name), root
            )
        model = self.env[model_name]

        group_definitions = self.env["res.groups"]._get_group_definitions()

        # model_groups/view_groups: access groups for the model/view
        model_groups = (
            node_info["model_groups"] if node_info else group_definitions.universe
        )
        view_groups = (
            node_info["view_groups"] if node_info else group_definitions.universe
        )
        parent_name_manager = node_info["name_manager"] if node_info else None

        # combine model access groups with this model's access groups
        model_groups &= self.env["ir.model.access"]._get_access_groups(model_name)

        name_manager = NameManager(
            model, parent=parent_name_manager, model_groups=model_groups
        )

        root_info = {
            "view_type": root.tag,
            "view_editable": editable and self._editable_node(root, name_manager),
            "mobile": options.get("mobile"),
            "model_groups": model_groups,
            "view_groups": view_groups,
            "name_manager": name_manager,
        }

        is_compute_warning_info = options.get("is_compute_warning_info")

        self._postprocess_debug_to_cache(root)

        # use a stack to recursively traverse the tree
        stack = [(root, view_groups, editable)]
        while stack:
            node, view_groups, editable = stack.pop()

            # compute default
            tag = node.tag
            had_parent = node.getparent() is not None
            node_info = dict(
                root_info,
                view_groups=view_groups,
                editable=editable and self._editable_node(node, name_manager),
            )

            node_groups = node.get("groups")
            if node_groups:
                node_info["view_groups"] &= group_definitions.parse(
                    node_groups, raise_if_not_found=False
                )

            # tag-specific postprocessing
            postprocessor = getattr(self, f"_postprocess_tag_{tag}", None)
            if postprocessor is not None:
                postprocessor(node, name_manager, node_info)
                if had_parent and node.getparent() is None:
                    # the node has been removed, stop processing here
                    continue

            # if present, iterate on node_info['children'] instead of node
            stack.extend(
                (child, node_info["view_groups"], node_info["editable"])
                for child in reversed(node_info.get("children", node))
            )

            if node_groups or root_info["model_groups"] != node_info["model_groups"]:
                groups = node_info["model_groups"] & node_info["view_groups"]
                node.set("__groups_key__", groups.key)

            self._postprocess_attributes(node, name_manager, node_info)

            if node_groups and is_compute_warning_info:
                # reset the groups attributes to display in log
                node.attrib["groups"] = node_groups

        missing_fields = self._add_missing_fields(root, name_manager)

        if is_compute_warning_info:
            for name, (missing_groups, reasons) in missing_fields.items():
                error_message = name_manager._error_message_group_inconsistency(
                    name, missing_groups, reasons
                )[0]
                if error_message:
                    if self.warning_info:
                        self.warning_info += Markup("<br/>\n<br/>\n")
                    self.warning_info += error_message.replace("\n", Markup("<br/>\n"))

        name_manager.update_available_fields()

        root.set("model_access_rights", model._name)

        if self._onchange_able_view(root):
            self._postprocess_on_change(root, model)

        return name_manager

    def _add_missing_fields(
        self, node: _Element, name_manager: NameManager
    ) -> dict[str, Any]:
        """Add the fields required for evaluating expressions in the view given by ``node``."""
        root = node
        missing_fields = name_manager.get_missing_fields()
        for name, (missing_groups, reasons) in missing_fields.items():
            if name not in name_manager.field_info:
                continue

            # If the available fields have different groups then to avoid it being missing for
            # certain users, we virtually add a field with common groups.
            name_manager.available_fields[name].setdefault("info", {})
            name_manager.available_fields[name].setdefault("groups", []).append(
                missing_groups
            )
            name_manager.available_names.add(name)

            readonly = True
            if filename_reasons := [r for r in reasons if r[1][0] == "filename"]:
                node = filename_reasons[-1][2]
                if node_readonly := node.get("readonly"):
                    readonly = node_readonly
                else:
                    field = name_manager.model._fields[node.get("name")]
                    if field.type == "binary":
                        readonly = field.readonly or False
            # If the field is not in the view without any group restriction,
            # add the field node with all mandatory groups (or without group if
            # the mandatory field does not have groups).
            attrs = {
                "name": name,
                ("invisible" if root.tag != "list" else "column_invisible"): "True",
                "readonly": str(readonly),
                "data-used-by": "; ".join(
                    f"{attr}={expr!r} ({node.tag},{node.get('name')})"
                    for _groups, (attr, expr), node in reasons
                ),
            }

            if missing_groups is not False:
                subset_groups = missing_groups.invert_intersect(
                    name_manager.model_groups
                )
                if subset_groups is None:
                    subset_groups = missing_groups
                if not subset_groups.is_universal():
                    attrs["__groups_key__"] = subset_groups.key

            item = etree.Element("field", attrs)
            item.tail = "\n"
            root.append(item)
        return missing_fields

    def _postprocess_on_change(self, arch: _Element, model: models.BaseModel) -> None:
        """Add attribute on_change="1" on fields that are dependencies of
        computed fields on the same view.
        """
        # map each field object to its corresponding nodes in arch
        field_nodes = collections.defaultdict(list)

        def collect(node: _Element, model: models.BaseModel) -> None:
            if node.tag == "field":
                field = model._fields.get(node.get("name"))
                if field:
                    field_nodes[field].append(node)
                    if field.relational:
                        model = self.env[field.comodel_name]
            for child in node:
                collect(child, model)

        collect(arch, model)

        for field, nodes in field_nodes.items():
            # if field should trigger an onchange, add on_change="1" on the
            # nodes referring to field
            model = self.env[field.model_name]
            if model._has_onchange(field, field_nodes):
                for node in nodes:
                    if not node.get("on_change"):
                        node.set("on_change", "1")

    def _get_x2many_missing_view_archs(
        self, field: Any, field_node: _Element, node_info: dict[str, Any]
    ) -> list[tuple[_Element, Self]]:
        """
        For x2many fields that require to have some multi-record arch (kanban or list) to display the records
        be available, this function fetches all arch that are needed and return them.
        The caller function is responsible to do what it needs with them.
        """
        current_view_types = [el.tag for el in _xpath_descendant_field(field_node)]
        missing_view_types = []
        if not any(
            view_type in current_view_types
            for view_type in field_node.get("mode", "kanban,list").split(",")
        ):
            missing_view_types.append(
                field_node.get(
                    "mode", "kanban" if node_info.get("mobile") else "list"
                ).split(",")[0]
            )

        if not missing_view_types:
            return []

        comodel = self.env[field.comodel_name].sudo(False)
        refs = self._get_view_refs(field_node)
        # Do not propagate <view_type>_view_ref of parent call to `_get_view`
        comodel = comodel.with_context(
            **{
                f"{view_type}_view_ref": refs.get(f"{view_type}_view_ref")
                for view_type in missing_view_types
            }
        )

        return [
            comodel._get_view(view_type=view_type) for view_type in missing_view_types
        ]

    def _postprocess_attributes(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        # get mandatory fields
        for attr, expr in node.items():
            if attr in VIEW_MODIFIERS or attr.startswith("decoration-"):
                vnames = get_expression_field_names(expr)
                name_manager.must_have_fields(node, vnames, node_info, (attr, expr))
            elif attr == "groups":
                node.attrib.pop("groups")

    # ------------------------------------------------------
    # Specific node postprocessors
    # ------------------------------------------------------
    def _postprocess_tag_calendar(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        for additional_field in (
            "date_start",
            "date_delay",
            "date_stop",
            "color",
            "all_day",
        ):
            if fname := node.get(additional_field):
                name_manager.has_field(node, fname, node_info)
        if fname := node.get("aggregate"):
            name_manager.has_field(node, fname.split(":")[0], node_info)
        for f in node:
            if f.tag == "filter":
                name_manager.has_field(node, f.get("name"), node_info)

    def _postprocess_tag_field(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        name = node.get("name")
        if not name:
            return

        attrs = {"id": node.get("id"), "select": node.get("select")}
        field = name_manager.model._fields.get(name)

        if field:
            if field.groups:
                group_definitions = self.env["res.groups"]._get_group_definitions()
                node_info["model_groups"] &= group_definitions.parse(
                    field.groups, raise_if_not_found=False
                )
            if (
                node_info.get("view_type") == "form"
                and field.type in ("one2many", "many2many")
                and not node.get("widget")
                and node.get("invisible") not in ("1", "True")
                and not name_manager.parent
            ):
                # Embed kanban/list/form views for visible x2many fields in form views
                # if no widget or the widget requires it.
                # So the web client doesn't have to call `get_views` for x2many fields not embedding their view
                # in the main form view.
                for arch, _view in self._get_x2many_missing_view_archs(
                    field, node, node_info
                ):
                    node.append(arch)

            if field.relational:
                domain = node.get("domain") or (
                    node_info["editable"] and field._description_domain(self.env)
                )
                if isinstance(domain, str):
                    vnames = get_expression_field_names(domain)
                    name_manager.must_have_fields(
                        node, vnames, node_info, ("domain", domain)
                    )
            if field.type == "properties":
                name_manager.must_have_fields(
                    node,
                    [field.definition_record],
                    node_info,
                    ("fieldname", field.name),
                )
            context = node.get("context")
            if context:
                vnames = get_expression_field_names(context)
                name_manager.must_have_fields(
                    node, vnames, node_info, ("context", context)
                )
            if field.type == "binary" and (field_filename := node.get("filename")):
                name_manager.must_have_fields(
                    node,
                    [field_filename],
                    node_info,
                    ("filename", field_filename),
                )

            for child in node:
                if child.tag in ("form", "list", "graph", "kanban", "calendar"):
                    node_info["children"] = []
                    self._postprocess_view(
                        child,
                        field.comodel_name,
                        editable=node_info["editable"],
                        node_info=node_info,
                    )

            if node_info["editable"] and field.type in (
                "many2one",
                "many2many",
            ):
                node.set("model_access_rights", field.comodel_name)

        name_manager.has_field(node, name, node_info, attrs)

    def _postprocess_tag_form(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        result = name_manager.model.view_header_get(False, node.tag)
        if result:
            node.set("string", result)

    def _postprocess_tag_groupby(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        # groupby nodes should be considered as nested view because they may
        # contain fields on the comodel
        name = node.get("name")
        field = name_manager.model._fields.get(name)
        if not field or not field.comodel_name:
            return
        # post-process the node as a nested view, and associate it to the field
        node_info["children"] = []
        self._postprocess_view(
            node, field.comodel_name, editable=False, node_info=node_info
        )
        name_manager.has_field(node, name, node_info)

    def _postprocess_tag_label(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node.get("for"):
            return
        field = name_manager.model._fields.get(node.get("for"))
        if field and field.groups:
            group_definitions = self.env["res.groups"]._get_group_definitions()
            node_info["model_groups"] &= group_definitions.parse(
                field.groups, raise_if_not_found=False
            )

    def _postprocess_tag_search(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        searchpanel = [child for child in node if child.tag == "searchpanel"]
        if searchpanel:
            self._postprocess_view(
                searchpanel[0],
                name_manager.model._name,
                editable=False,
                node_info=node_info,
            )
            node_info["children"] = [
                child for child in node if child.tag != "searchpanel"
            ]

    def _postprocess_tag_list(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        # reuse form view post-processing
        self._postprocess_tag_form(node, name_manager, node_info)

    # -------------------------------------------------------------------
    # view editability
    # -------------------------------------------------------------------

    def _editable_node(self, node: _Element, name_manager: NameManager) -> bool:
        """Return whether the given node must be considered editable."""
        func = getattr(self, f"_editable_tag_{node.tag}", None)
        if func is not None:
            return func(node, name_manager)
        # by default views are non-editable
        return node.tag not in (item[0] for item in self._fields["type"].selection)

    def _editable_tag_form(self, node: _Element, name_manager: NameManager) -> bool:
        return True

    def _editable_tag_list(
        self, node: _Element, name_manager: NameManager
    ) -> str | None:
        return node.get("editable") or node.get("multi_edit")

    def _editable_tag_field(self, node: _Element, name_manager: NameManager) -> bool:
        field = name_manager.model._fields.get(node.get("name"))
        return field is None or (
            field.is_editable() and node.get("readonly") not in ("1", "True")
        )

    def _onchange_able_view(self, node: _Element) -> bool | None:
        func = getattr(self, f"_onchange_able_view_{node.tag}", None)
        if func is not None:
            return func(node)
        return None

    def _onchange_able_view_form(self, node: _Element) -> bool:
        return True

    def _onchange_able_view_list(self, node: _Element) -> bool:
        return True

    def _onchange_able_view_kanban(self, node: _Element) -> bool:
        return True

    def _modifiers_from_model(self, node: _Element) -> list[str]:
        modifier_names = []
        if node.tag in ("kanban", "list", "form"):
            modifier_names += ["readonly", "required"]
        return modifier_names

    # -------------------------------------------------------------------
    # view validation
    # -------------------------------------------------------------------

    def _validate_view(
        self,
        node: _Element,
        model_name: str,
        view_type: str | None = None,
        editable: bool = True,
        node_info: dict[str, Any] | None = None,
    ) -> NameManager:
        """Validate the given architecture node, and return its corresponding
        NameManager.

        :param self: the view being validated
        :param node: the combined architecture as an etree
        :param model_name: the reference model name for the given architecture
        :param view_type:
        :param editable: whether the view is considered editable
        :param node_info:
        :return: the combined architecture's NameManager
        """
        self.ensure_one()

        view_type = view_type or self.type
        if node.tag != view_type:
            self._raise_view_error(
                _(
                    "The root node of a %(view_type)s view should be a <%(view_type)s>, not a <%(tag)s>",
                    view_type=view_type,
                    tag=node.tag,
                ),
                node,
            )

        if model_name not in self.env:
            self._raise_view_error(
                _("Model not found: %(model)s", model=model_name), node
            )

        group_definitions = self.env["res.groups"]._get_group_definitions()

        # model_groups/view_groups: access groups for the model/view
        validate = node_info["validate"] if node_info else False
        model_groups = (
            node_info["model_groups"] if node_info else group_definitions.universe
        )
        view_groups = (
            node_info["view_groups"] if node_info else group_definitions.universe
        )
        parent_name_manager = node_info["name_manager"] if node_info else None

        # combine model access groups with this model's access groups
        model_groups &= self.env["ir.model.access"]._get_access_groups(model_name)

        # fields_get() optimization: validation does not require translations
        model = self.env[model_name].with_context(lang=None)
        name_manager = NameManager(
            model, parent=parent_name_manager, model_groups=model_groups
        )

        view_type = node.tag
        # use a stack to recursively traverse the tree
        stack = [(node, view_groups, editable, validate)]
        while stack:
            node, view_groups, editable, validate = stack.pop()

            # compute default
            tag = node.tag
            validate = validate or node.get("__validate__")
            node_info = {
                "editable": editable and self._editable_node(node, name_manager),
                "validate": validate,
                "view_type": view_type,
                "model_groups": model_groups,
                "view_groups": view_groups,
                "name_manager": name_manager,
            }

            if groups := node.get("groups"):
                for group_name in groups.replace("!", "").split(","):
                    name_manager.must_exist_group(group_name, node)
                node_info["view_groups"] &= group_definitions.parse(
                    groups, raise_if_not_found=False
                )

            # tag-specific validation
            validator = getattr(self, f"_validate_tag_{tag}", None)
            if validator is not None:
                validator(node, name_manager, node_info)

            if validate:
                self._validate_attributes(node, name_manager, node_info)

            stack.extend(
                (
                    child,
                    node_info["view_groups"],
                    node_info["editable"],
                    validate,
                )
                for child in reversed(node)
            )

        name_manager.check(self)

        return name_manager

    # ------------------------------------------------------
    # Node validator
    # ------------------------------------------------------
    def _validate_tag_form(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        pass

    def _validate_tag_list(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        # reuse form view validation
        self._validate_tag_form(node, name_manager, node_info)
        if not node_info["validate"]:
            return
        # inline list views inside form views aren't rng validated, so we must validate the
        # editable attribute in python
        editable_attr = node.get("editable")
        if editable_attr and editable_attr not in ["top", "bottom"]:
            msg = _(
                'The "editable" attribute of list views must be "top" or "bottom", received %(value)s',
                value=editable_attr,
            )
            self._raise_view_error(msg, node)
        allowed_tags = (
            "field",
            "button",
            "control",
            "groupby",
            "widget",
            "header",
        )
        for child in node.iterchildren(tag=etree.Element):
            if child.tag not in allowed_tags and not isinstance(child, etree._Comment):
                msg = _(
                    "List child can only have one of %(tags)s tag (not %(wrong_tag)s)",
                    tags=", ".join(allowed_tags),
                    wrong_tag=child.tag,
                )
                self._raise_view_error(msg, child)

    def _validate_tag_graph(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        for child in node.iterchildren(tag=etree.Element):
            if child.tag != "field" and not isinstance(child, etree._Comment):
                msg = _(
                    "A <graph> can only contains <field> nodes, found a <%s>",
                    child.tag,
                )
                self._raise_view_error(msg, child)

    def _validate_tag_calendar(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        for additional_field in (
            "date_start",
            "date_delay",
            "date_stop",
            "color",
            "all_day",
        ):
            if fnames := node.get(additional_field):
                name_manager.has_field(node, fnames.split(".", 1)[0], node_info)
        for f in node:
            if f.tag == "filter":
                name_manager.has_field(node, f.get("name"), node_info)

    def _validate_tag_search(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if node_info["validate"] and not node.iterdescendants(tag="field"):
            # the field of the search view may be within a group node, which is why we must check
            # for all descendants containing a node with a field tag, if this is not the case
            # then a search is not possible.
            self._log_view_warning(
                "Search tag requires at least one field element", node
            )

        searchpanels = [child for child in node if child.tag == "searchpanel"]
        if searchpanels:
            if len(searchpanels) > 1:
                self._raise_view_error(
                    _("Search tag can only contain one search panel"), node
                )
            node.remove(searchpanels[0])
            self._validate_view(
                searchpanels[0],
                name_manager.model._name,
                view_type="searchpanel",
                node_info=node_info,
                editable=False,
            )

    def _validate_tag_field(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        validate = node_info["validate"]

        name = node.get("name")
        if not name:
            self._raise_view_error(
                _('Field tag must have a "name" attribute defined'), node
            )

        field = name_manager.model._fields.get(name)
        if field:
            if field.groups:
                group_definitions = self.env["res.groups"]._get_group_definitions()
                node_info["model_groups"] &= group_definitions.parse(
                    field.groups, raise_if_not_found=False
                )

            if validate and field.relational:
                domain = node.get("domain") or (
                    node_info["editable"] and field._description_domain(self.env)
                )
                if isinstance(domain, str):
                    # dynamic domain: in [('foo', '=', bar)], field 'foo' must
                    # exist on the comodel and field 'bar' must be in the view
                    desc = (
                        f'domain of <field name="{name}">'
                        if node.get("domain")
                        else f"domain of python field {name!r}"
                    )
                    self._validate_domain_identifiers(
                        node,
                        name_manager,
                        domain,
                        desc,
                        field.comodel_name,
                        node_info,
                    )

            elif validate and node.get("domain"):
                msg = _(
                    'Domain on non-relational field "%(name)s" makes no sense (domain:%(domain)s)',
                    name=name,
                    domain=node.get("domain"),
                )
                self._raise_view_error(msg, node)

            if field.type == "properties" and node_info["view_type"] != "search":
                name_manager.must_have_fields(
                    node,
                    {field._description_definition_record},
                    node_info,
                    use=f"definition record of {field.name}",
                )

            for child in node:
                if child.tag not in (
                    "form",
                    "list",
                    "graph",
                    "kanban",
                    "calendar",
                ):
                    continue
                node.remove(child)
                self._validate_view(
                    child,
                    field.comodel_name,
                    view_type=child.tag,
                    editable=node_info["editable"],
                    node_info=node_info,
                )

        elif validate and name not in name_manager.field_info:
            msg = _(
                'Field "%(field_name)s" does not exist in model "%(model_name)s"',
                field_name=name,
                model_name=name_manager.model._name,
            )
            self._raise_view_error(msg, node)

        name_manager.has_field(
            node,
            name,
            node_info,
            {"id": node.get("id"), "select": node.get("select")},
        )

    def _validate_tag_filter(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        domain = node.get("domain")
        if domain:
            name = node.get("name")
            desc = f'domain of <filter name="{name}">' if name else "domain of <filter>"
            self._validate_domain_identifiers(
                node,
                name_manager,
                domain,
                desc,
                name_manager.model._name,
                node_info,
            )
        if node.get("date") and (default_periods := node.get("default_period")):
            custom_options = {f"custom_{child.attrib['name']}" for child in node}
            for default_period in default_periods.split(","):
                if not re.fullmatch(
                    r"(year|month)((-|\+)[1-9]\d*)?", default_period
                ) and default_period not in custom_options | {
                    "first_quarter",
                    "second_quarter",
                    "third_quarter",
                    "fourth_quarter",
                }:
                    msg = _(
                        "Invalid default period %(default_period)s for date filter",
                        default_period=default_period,
                    )
                    self._raise_view_error(msg, node)

    def _validate_tag_button(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        name = node.get("name")
        special = node.get("special")
        type_ = node.get("type")
        if special:
            if special not in ("cancel", "save", "add"):
                self._raise_view_error(
                    _("Invalid special '%(value)s' in button", value=special),
                    node,
                )
        elif type_:
            if (type_ not in {"action", "object"}) or not name:
                return
            elif type_ == "object":
                func = getattr(name_manager.model, name, None)
                if not func:
                    msg = _(
                        "%(action_name)s is not a valid action on %(model_name)s",
                        action_name=name,
                        model_name=name_manager.model._name,
                    )
                    self._raise_view_error(msg, node)
                # get_public_method(name_manager.model, name) is too slow for this validation, a more naive check is acceptable.
                if name.startswith("_") or (
                    hasattr(func, "_api_private") and func._api_private
                ):
                    msg = _(
                        "%(method)s on %(model)s is private and cannot be called from a button",
                        method=name,
                        model=name_manager.model._name,
                    )
                    self._raise_view_error(msg, node)
                try:
                    inspect.signature(func).bind()
                except TypeError:
                    msg = "%s on %s has parameters and cannot be called from a button"
                    self._log_view_warning(msg % (name, name_manager.model._name), node)
            elif type_ == "action":
                name_manager.must_exist_action(name, node)

            name_manager.has_action(name)

        if node.get("icon"):
            description = f"A button with icon attribute ({node.get('icon')})"
            self._validate_fa_class_accessibility(node, description)

    def _validate_tag_groupby(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        # groupby nodes should be considered as nested view because they may
        # contain fields on the comodel
        name = node.get("name")
        if not name:
            return
        field = name_manager.model._fields.get(name)
        if field:
            if node_info["validate"]:
                if field.type != "many2one":
                    msg = _(
                        "Field '%(name)s' found in 'groupby' node can only be of type many2one, found %(type)s",
                        name=field.name,
                        type=field.type,
                    )
                    self._raise_view_error(msg, node)
                domain = node_info["editable"] and field._description_domain(self.env)
                if isinstance(domain, str):
                    desc = f"domain of python field '{name}'"
                    self._validate_domain_identifiers(
                        node,
                        name_manager,
                        domain,
                        desc,
                        field.comodel_name,
                        node_info,
                    )

            # move all children nodes into a new node <groupby>
            groupby_node = E.groupby(*node)
            # validate the node as a nested view
            self._validate_view(
                groupby_node,
                field.comodel_name,
                view_type="groupby",
                editable=False,
                node_info=node_info,
            )
            name_manager.has_field(node, name, node_info)

        elif node_info["validate"]:
            msg = _(
                "Field '%(field)s' found in 'groupby' node does not exist in model %(model)s",
                field=name,
                model=name_manager.model._name,
            )
            self._raise_view_error(msg, node)

    def _validate_tag_searchpanel(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        for child in node.iterchildren(tag=etree.Element):
            if child.get("domain") and child.get("select") != "multi":
                msg = _(
                    "Searchpanel items with a domain attribute must have select='multi'."
                )
                self._raise_view_error(msg, child)

    def _validate_tag_label(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        # replace return not arch.xpath('//label[not(@for) and not(descendant::input)]')
        for_ = node.get("for")
        if not for_:
            msg = _(
                'Label tag must contain a "for". To match label style '
                "without corresponding field or button, use 'class=\"o_form_label\"'."
            )
            self._raise_view_error(msg, node)
        else:
            name_manager.must_have_name(for_, '<label for="...">')

    def _validate_tag_page(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        if node.getparent() is None or node.getparent().tag != "notebook":
            self._raise_view_error(_("Page direct ancestor must be notebook"), node)

    def _validate_tag_img(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if node_info["validate"] and not any(node.get(alt) for alt in att_names("alt")):
            self._log_view_warning("<img> tag must contain an alt attribute", node)

    def _validate_tag_a(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        # ('calendar', 'form', 'graph', 'kanban', 'pivot', 'search', 'list', 'activity')  # noqa: ERA001
        if node_info["validate"] and any(
            "btn" in node.get(cl, "") for cl in att_names("class")
        ):
            if node.get("role") != "button":
                msg = '"<a>" tag with "btn" class must have "button" role'
                self._log_view_warning(msg, node)

    def _validate_tag_ul(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if node_info["validate"]:
            # was applied to all nodes, but in practice only used on div and ul
            self._check_dropdown_menu(node)

    def _validate_tag_div(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if node_info["validate"]:
            self._check_dropdown_menu(node)
            self._check_progress_bar(node)

    # ------------------------------------------------------
    # Validation tools
    # ------------------------------------------------------

    def _check_dropdown_menu(self, node: _Element) -> None:
        # ('calendar', 'form', 'graph', 'kanban', 'pivot', 'search', 'list', 'activity')  # noqa: ERA001
        if any("dropdown-menu" in node.get(cl, "") for cl in att_names("class")):
            if node.get("role") != "menu":
                msg = "dropdown-menu class must have menu role"
                self._log_view_warning(msg, node)

    def _check_progress_bar(self, node: _Element) -> None:
        if any("o_progressbar" in node.get(cl, "") for cl in att_names("class")):
            if node.get("role") != "progressbar":
                msg = "o_progressbar class must have progressbar role"
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in att_names("aria-valuenow")):
                msg = "o_progressbar class must have aria-valuenow attribute"
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in att_names("aria-valuemin")):
                msg = "o_progressbar class must have aria-valuemin attribute"
                self._log_view_warning(msg, node)
            if not any(node.get(at) for at in att_names("aria-valuemax")):
                msg = "o_progressbar class must have aria-valuemaxattribute"
                self._log_view_warning(msg, node)

    def _is_qweb_based_view(self, view_type: str) -> bool:
        return view_type == "kanban"

    def _validate_attributes(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        """Generic validation of node attributes."""

        # python expression used in for readonly, invisible, ...
        # and thus are only executed client side
        for attr in VIEW_MODIFIERS:
            py_expression = node.attrib.get(attr)
            if py_expression:
                self._validate_expression(
                    node,
                    name_manager,
                    py_expression,
                    f"modifier {attr!r}",
                    node_info,
                )

        for attr, expr in node.items():
            if attr in ("class", "t-att-class", "t-attf-class"):
                self._validate_classes(node, expr)

            elif attr == "context":
                try:
                    vnames = get_expression_field_names(expr)
                except SyntaxError as e:
                    message = _(
                        "Invalid context: “%(expr)s” is not a valid Python expression \n\n %(error)s",
                        expr=expr,
                        error=e,
                    )
                    self._raise_view_error(message)
                if vnames:
                    name_manager.must_have_fields(
                        node, vnames, node_info, f"context ({expr})"
                    )
                for key, val_ast in get_dict_asts(expr).items():
                    if key == "group_by":  # only in context
                        if not isinstance(val_ast, ast.Constant) or not isinstance(
                            val_ast.value, str
                        ):
                            msg = _(
                                '"group_by" value must be a string %(attribute)s=“%(value)s”',
                                attribute=attr,
                                value=expr,
                            )
                            self._raise_view_error(msg, node)
                        group_by = val_ast.value
                        fname = group_by.split(":")[0]
                        if fname not in name_manager.model._fields:
                            msg = _(
                                'Unknown field “%(field)s” in "group_by" value in %(attribute)s=“%(value)s”',
                                field=fname,
                                attribute=attr,
                                value=expr,
                            )
                            self._raise_view_error(msg, node)

            elif attr in ("col", "colspan"):
                # col check is mainly there for the tag 'group', but previous
                # check was generic in view form
                if not expr.isdigit():
                    self._raise_view_error(
                        _(
                            "“%(attribute)s” value must be an integer (%(value)s)",
                            attribute=attr,
                            value=expr,
                        ),
                        node,
                    )

            elif attr.startswith("decoration-"):
                vnames = get_expression_field_names(expr)
                if vnames:
                    name_manager.must_have_fields(
                        node, vnames, node_info, f"{attr}={expr!r}"
                    )

            elif attr == "data-bs-toggle" and expr == "tab":
                if node.get("role") != "tab":
                    msg = 'tab link (data-bs-toggle="tab") must have "tab" role'
                    self._log_view_warning(msg, node)
                aria_control = node.get("aria-controls") or node.get(
                    "t-att-aria-controls"
                )
                if not aria_control and not node.get("t-attf-aria-controls"):
                    msg = 'tab link (data-bs-toggle="tab") must have "aria_control" defined'
                    self._log_view_warning(msg, node)
                if aria_control and "#" in aria_control:
                    msg = 'aria-controls in tablink cannot contains "#"'
                    self._log_view_warning(msg, node)

            elif attr == "role" and expr in ("presentation", "none"):
                msg = (
                    "A role cannot be `none` or `presentation`. "
                    "All your elements must be accessible with screen readers, describe it."
                )
                self._log_view_warning(msg, node)

            elif attr == "group":
                msg = "attribute 'group' is not valid.  Did you mean 'groups'?"
                self._log_view_warning(msg, node)

            elif re.match(
                r"^(t\-att\-|t\-attf\-)?data-tooltip(-template|-info)?$", attr
            ):
                self._raise_view_error(
                    _("Forbidden attribute used in arch (%s).", attr), node
                )

            elif attr.startswith("t-"):
                self._validate_qweb_directive(node, attr, node_info["view_type"])
                if re.search(COMP_REGEX, expr):
                    self._raise_view_error(
                        _("Forbidden use of `__comp__` in arch."), node
                    )

    def _validate_classes(self, node: _Element, expr: str) -> None:
        """Validate the classes present on node."""
        classes = set(expr.split(" "))
        # Be careful: not always true if it is an expression
        # example: <div t-attf-class="{{!selection_mode ? 'oe_kanban_color_' + kanban_getcolor(record.color.raw_value) : ''}} oe_kanban_card oe_kanban_global_click oe_applicant_kanban oe_semantic_html_override">
        if "modal" in classes and node.get("role") != "dialog":
            msg = '"modal" class should only be used with "dialog" role'
            self._log_view_warning(msg, node)

        if "modal-header" in classes and node.tag != "header":
            msg = '"modal-header" class should only be used in "header" tag'
            self._log_view_warning(msg, node)

        if "modal-body" in classes and node.tag != "main":
            msg = '"modal-body" class should only be used in "main" tag'
            self._log_view_warning(msg, node)

        if "modal-footer" in classes and node.tag != "footer":
            msg = '"modal-footer" class should only be used in "footer" tag'
            self._log_view_warning(msg, node)

        if "tab-pane" in classes and node.get("role") != "tabpanel":
            msg = '"tab-pane" class should only be used with "tabpanel" role'
            self._log_view_warning(msg, node)

        if "nav-tabs" in classes and node.get("role") != "tablist":
            msg = 'A tab list with class nav-tabs must have role="tablist"'
            self._log_view_warning(msg, node)

        if any(klass.startswith("alert-") for klass in classes):
            if (
                node.get("role") not in ("alert", "alertdialog", "status")
                and "alert-link" not in classes
            ):
                msg = (
                    "An alert (class alert-*) must have an alert, alertdialog or "
                    "status role or an alert-link class. Please use alert and "
                    "alertdialog only for what expects to stop any activity to "
                    "be read immediately."
                )
                self._log_view_warning(msg, node)

        if any(klass.startswith("fa-") for klass in classes):
            description = f"A <{node.tag}> with fa class ({expr})"
            self._validate_fa_class_accessibility(node, description)

        if any(klass.startswith("btn") for klass in classes):
            if (
                node.tag in ("a", "button", "select")
                or (
                    node.tag == "input"
                    and node.get("type")
                    in (
                        "button",
                        "submit",
                        "reset",
                    )
                )
                or any(
                    klass in classes
                    for klass in ("btn-group", "btn-toolbar", "btn-addr")
                )
                or (node.tag == "field" and node.get("widget") == "url")
            ):
                pass
            else:
                msg = (
                    "A simili button must be in tag a/button/select or tag `input` "
                    "with type button/submit/reset or have class in "
                    "btn-group/btn-toolbar/btn-addr"
                )
                self._log_view_warning(msg, node)

    def _validate_fa_class_accessibility(
        self, node: _Element, description: str
    ) -> None:
        valid_aria_attrs = {
            *att_names("title"),
            *att_names("aria-label"),
            *att_names("aria-labelledby"),
        }
        valid_t_attrs = {"t-value", "t-raw", "t-field", "t-esc", "t-out"}

        ## Following or preceding text
        if (node.tail or "").strip() or (node.getparent().text or "").strip():
            # text<i class="fa-..."/> or <i class="fa-..."/>text or
            return

        ## Following or preceding text in span
        def has_text(elem: _Element | None) -> bool:
            if elem is None:
                return False
            if elem.tag == "span" and elem.text:
                return True
            if elem.tag in ["field", "label"] and elem.get("string"):
                return True
            return bool(elem.tag == "t" and (elem.get("t-esc") or elem.get("t-raw")))

        if has_text(node.getnext()) or has_text(node.getprevious()):
            return

        def has_title_or_aria_label(node: _Element) -> bool:
            return any(node.get(attr) for attr in valid_aria_attrs)

        ## Aria label can be on ancestors
        if any(map(has_title_or_aria_label, node.iterancestors())):
            return

        if node.get("string"):
            return

        ## And we ignore all elements with describing in children
        def contains_description(node: _Element, depth: int = 0) -> bool:
            if depth > 2:
                _logger.warning("excessive depth in fa")
            if any(node.get(attr) for attr in valid_t_attrs):
                return True
            if has_title_or_aria_label(node):
                return True
            if node.tag in ("label", "field"):
                return True
            if node.text:  # not sure, does it match *[text()]
                return True
            return any(contains_description(child, depth + 1) for child in node)

        if contains_description(node):
            return

        msg = "%s must have title in its tag, parents, descendants or have text"
        self._log_view_warning(msg % description, node)

    def _validate_qweb_directive(
        self, node: _Element, directive: str, view_type: str
    ) -> None:
        """Some views (e.g. kanban, form) generate owl templates from the archs.
        However, we don't want to see owl directives directly written in archs.
        There are exceptions though, e.g. the kanban arch defines qweb templates.
        We thus here validate that the given directive is allowed, according to the view_type.
        """
        allowed_directives = ["t-translation"]
        if self._is_qweb_based_view(view_type):
            allowed_directives.extend(
                [
                    "t-name",
                    "t-esc",
                    "t-out",
                    "t-set",
                    "t-value",
                    "t-if",
                    "t-else",
                    "t-elif",
                    "t-foreach",
                    "t-as",
                    "t-key",
                    "t-att.*",
                    "t-call",
                    "t-debug",
                ]
            )
        if not next(
            filter(lambda regex: re.match(regex, directive), allowed_directives),
            None,
        ):
            self._raise_view_error(
                _("Forbidden owl directive used in arch (%s).", directive), node
            )

    def _validate_expression(
        self,
        node: _Element,
        name_manager: NameManager,
        py_expression: str,
        use: str,
        node_info: dict[str, Any],
    ) -> None:
        try:
            if py_expression.lower() in ("0", "false", "1", "true"):
                # most (~95%) elements are 1/True/0/False
                return
            fnames = get_expression_field_names(py_expression)
        except (SyntaxError, ValueError, AttributeError) as e:
            msg = _(
                "Invalid %(use)s: “%(expr)s”\n%(error)s",
                use=use,
                expr=py_expression,
                error=e,
            )
            self._raise_view_error(msg, node, from_exception=e)
        name_manager.must_have_fields(
            node, fnames, node_info, f"{use} ({py_expression})"
        )

    def _validate_domain_identifiers(
        self,
        node: _Element,
        name_manager: NameManager,
        domain: str,
        use: str,
        target_model: str,
        node_info: dict[str, Any],
    ) -> None:
        try:
            fnames, vnames = get_domain_value_names(domain)
        except (SyntaxError, ValueError, AttributeError) as e:
            msg = _(
                "Invalid %(use)s: “%(expr)s”\n%(error)s",
                use=use,
                expr=domain,
                error=e,
            )
            self._raise_view_error(msg, node, from_exception=e)

        self._check_field_paths(node, fnames, target_model, f"{use} ({domain})")
        name_manager.must_have_fields(node, vnames, node_info, f"{use} ({domain})")

    def _check_field_paths(
        self, node: _Element, field_paths: set[str], model_name: str, use: str
    ) -> None:
        """Check whether the given field paths (dot-separated field names)
        correspond to actual sequences of fields on the given model.
        """
        for field_path in field_paths:
            names = field_path.split(".")
            Model = self.pool[model_name]
            if names[0] == "parent":
                continue
            for index, name in enumerate(names):
                if Model is None:
                    msg = _(
                        "Non-relational field “%(field)s” in path “%(field_path)s” in %(use)s)",
                        field=names[index - 1],
                        field_path=field_path,
                        use=use,
                    )
                    self._raise_view_error(msg, node)
                try:
                    field = Model._fields[name]
                except KeyError:
                    msg = _(
                        'Unknown field "%(model)s.%(field)s" in %(use)s)',
                        model=Model._name,
                        field=name,
                        use=use,
                    )
                    self._raise_view_error(msg, node)
                if not field._description_searchable:
                    msg = _(
                        "Unsearchable field “%(field)s” in path “%(field_path)s” in %(use)s)",
                        field=name,
                        field_path=field_path,
                        use=use,
                    )
                    self._raise_view_error(msg, node)
                Model = self.pool.get(field.comodel_name)

    # ------------------------------------------------------
    # QWeb template views
    # ------------------------------------------------------

    def _read_template_keys(self) -> list[str]:
        """Return the list of context keys to use for caching ``_read_template``."""
        return ["lang", "inherit_branding", "edit_translations"]

    def _get_view_etrees(self) -> list[_Element]:
        if not self:
            return []
        arch_trees = self._get_combined_archs()
        for arch_tree in arch_trees:
            self.distribute_branding(arch_tree)
        return arch_trees

    def _contains_branded(self, node: _Element) -> bool:
        return (
            node.tag == "t"
            or "t-raw" in node.attrib
            or "t-call" in node.attrib
            or any(self.is_node_branded(child) for child in node.iterdescendants())
        )

    def _pop_view_branding(self, element: _Element) -> dict[str, str]:
        return {
            attribute: element.attrib.pop(attribute)
            for attribute in MOVABLE_BRANDING
            if element.get(attribute)
        }

    def distribute_branding(
        self,
        e: _Element,
        branding: dict[str, str] | None = None,
        parent_xpath: str = "",
        index_map: Any = ConstantMapping(1),
    ) -> None:
        if e.get("t-ignore") or e.tag == "head":
            # remove any view branding possibly injected by inheritance
            attrs = set(MOVABLE_BRANDING)
            for descendant in e.iterdescendants(tag=etree.Element):
                if not attrs.intersection(descendant.attrib):
                    continue
                self._pop_view_branding(descendant)

            # Remove the processing instructions indicating where nodes were
            # removed (see apply_inheritance_specs)
            for descendant in e.iterdescendants(tag=etree.ProcessingInstruction):
                if descendant.target == "apply-inheritance-specs-node-removal":
                    descendant.getparent().remove(descendant)
            return

        node_path = e.get("data-oe-xpath")
        if node_path is None:
            # Handle special case for jump points defined by the magic template
            # <t>$0</t>. No branding is allowed in this case since it points to
            # a generic template.
            if e.get("data-oe-no-branding"):
                e.attrib.pop("data-oe-no-branding")
                return
            node_path = f"{parent_xpath}/{e.tag}[{index_map[e.tag]}]"
        if branding:
            if e.get("t-field"):
                e.set("data-oe-xpath", node_path)
            elif not e.get("data-oe-model"):
                e.attrib.update(branding)
                e.set("data-oe-xpath", node_path)
        if not e.get("data-oe-model"):
            return

        if {"t-esc", "t-raw", "t-out"}.intersection(e.attrib):
            # nodes which fully generate their content and have no reason to
            # be branded because they can not sensibly be edited
            self._pop_view_branding(e)
        elif self._contains_branded(e):
            # if a branded element contains branded elements distribute own
            # branding to children unless it's t-raw, then just remove branding
            # on current element
            distributed_branding = self._pop_view_branding(e)

            if "t-raw" not in e.attrib:
                # running index by tag type, for XPath query generation
                indexes = collections.defaultdict(lambda: 0)
                for child in e.iterchildren(etree.Element, etree.ProcessingInstruction):
                    if child.get("data-oe-xpath"):
                        # injected by view inheritance, skip otherwise
                        # generated xpath is incorrect
                        self.distribute_branding(child)
                    elif child.tag is etree.ProcessingInstruction:
                        # If a node is known to have been replaced during
                        # applying an inheritance, increment its index to
                        # compute an accurate xpath for subsequent nodes
                        if child.target == "apply-inheritance-specs-node-removal":
                            indexes[child.text] += 1
                            e.remove(child)
                    else:
                        indexes[child.tag] += 1
                        self.distribute_branding(
                            child,
                            distributed_branding,
                            parent_xpath=node_path,
                            index_map=indexes,
                        )

    def is_node_branded(self, node: _Element) -> bool:
        """Finds out whether a node is branded or qweb-active (bears a
        @data-oe-model or a @t-* *which is not t-field* as t-field does not
        section out views)

        :param node: an etree-compatible element to test
        :type node: _Element
        :rtype: bool
        """
        return any(
            (attr in ("data-oe-model", "groups") or (attr.startswith("t-")))
            for attr in node.attrib
        ) or (
            node.tag is etree.ProcessingInstruction
            and node.target == "apply-inheritance-specs-node-removal"
        )

    @api.readonly
    @api.model
    def render_public_asset(
        self, template: int | str, values: dict[str, Any] | None = None
    ) -> Markup:
        self._get_template_view(template)._check_view_access()
        return self.env["ir.qweb"].sudo()._render(template, values)

    def _render_template(
        self, template: int | str, values: dict[str, Any] | None = None
    ) -> Markup:
        return self.env["ir.qweb"]._render(template, values)

    # ------------------------------------------------------
    # Misc
    # ------------------------------------------------------

    @api.model
    def _validate_custom_views(self, model: str) -> bool:
        """Validate architecture of custom views (= without xml id) for a given model.
        This method is called at the end of registry update.
        """
        rec = self.browse(
            id_
            for (id_,) in self.env.execute_query(
                SQL(
                    """
                   SELECT max(v.id)
                     FROM ir_ui_view v
                LEFT JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
                    WHERE md.module IN (SELECT name FROM ir_module_module) IS NOT TRUE
                      AND v.model = %s
                      AND v.active = true
                 GROUP BY coalesce(v.inherit_id, v.id)
                 """,
                    model,
                )
            )
        )
        return rec.with_context({"load_all_views": True})._check_xml()

    @api.model
    def _validate_module_views(self, module: str) -> None:
        """Validate the architecture of all the views of a given module that
        are impacted by view updates, but have not been checked yet.
        """
        if not self.pool._init:
            raise RuntimeError(
                "_validate_module_views() must only be called during module initialization"
            )

        # only validate the views that still exist...
        prefix = module + "."
        prefix_len = len(prefix)
        names = tuple(
            xmlid[prefix_len:]
            for xmlid in self.pool.loaded_xmlids
            if xmlid.startswith(prefix)
        )
        if not names:
            return

        # retrieve the views with an XML id that has not been checked yet, i.e.,
        # the views with noupdate=True on their xml id
        views = self.browse(
            id_
            for (id_,) in self.env.execute_query(
                SQL(
                    """
            SELECT v.id
            FROM ir_ui_view v
            JOIN ir_model_data md ON (md.model = 'ir.ui.view' AND md.res_id = v.id)
            WHERE md.module = %s AND md.name = ANY(%s) AND md.noupdate
        """,
                    module,
                    list(names),
                )
            )
        )

        views._check_xml()

    def _create_all_specific_views(self, processed_modules: list[str]) -> None:
        """To be overridden and have specific view behaviour on create."""
        pass

    def _get_specific_views(self) -> Self:
        """Given a view, return a record set containing all the specific views
        for that view's key.
        """
        self.ensure_one()
        # Only qweb views have a specific conterpart
        if self.type != "qweb":
            return self.env["ir.ui.view"]
        # A specific view can have a xml_id if exported/imported but it will not be equals to it's key (only generic view will).
        return (
            self.with_context(active_test=False)
            .search([("key", "=", self.key)])
            .filtered(lambda r: r.xml_id != r.key)
        )

    def _load_records_write(self, values: dict[str, Any]) -> None:
        """During module update, when updating a generic view, we should also
        update its specific views (COW'd).
        Note that we will only update unmodified fields. That will mimic the
        noupdate behavior on views having an ir.model.data.
        """
        if self.type == "qweb":
            for cow_view in self._get_specific_views():
                authorized_vals = {}
                for key in values:
                    if key != "inherit_id" and cow_view[key] == self[key]:
                        authorized_vals[key] = values[key]
                # if inherit_id update, replicate change on cow view but
                # only if that cow view inherit_id wasn't manually changed
                inherit_id = values.get("inherit_id")
                if (
                    inherit_id
                    and self.inherit_id.id != inherit_id
                    and cow_view.inherit_id.key == self.inherit_id.key
                ):
                    self._load_records_write_on_cow(
                        cow_view, inherit_id, authorized_vals
                    )
                else:
                    cow_view.with_context(no_cow=True).write(authorized_vals)
        super()._load_records_write(values)

    def _load_records_write_on_cow(
        self, cow_view: Self, inherit_id: int, values: dict[str, Any]
    ) -> None:
        # for modules updated before `website`, we need to
        # store the change to replay later on cow views
        if not hasattr(self.pool, "website_views_to_adapt"):
            self.pool.website_views_to_adapt = []
        self.pool.website_views_to_adapt.append(
            (
                cow_view.id,
                inherit_id,
                values,
            )
        )
