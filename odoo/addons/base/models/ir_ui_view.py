import collections
import copy
import functools
import logging
import pprint
import re
import types
import typing
import uuid
from collections.abc import Callable, Collection
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from lxml import etree
from lxml.builder import E
from lxml.etree import _Element
from markupsafe import Markup

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import (
    AccessError,
    MissingError,
    UserError,
    ValidationError,
)
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.text import split_refs
from odoo.modules.module import get_resource_from_path
from odoo.tools import SQL, _, config, frozendict, partition, unique
from odoo.tools.convert import _fix_multiple_roots
from odoo.tools.misc import ConstantMapping, file_path
from odoo.tools.template_inheritance import apply_inheritance_specs, locate_node
from odoo.tools.translate import TRANSLATED_ATTRS, xml_translate
from odoo.tools.view_ir import (
    Applied,
    Node,
    Patch,
    apply_specs,
    from_arch,
    identify,
    to_arch,
)
from odoo.tools.view_validation import (
    get_class_accessibility_warnings,
    get_domain_value_names,
    get_dropdown_menu_warnings,
    get_expression_field_names,
    get_fa_class_accessibility_warnings,
    get_progress_bar_warnings,
    valid_view,
)

from .ir_ui_view_arch import ELEMENT_HANDLERS, attribute_check_for
from .ir_ui_view_name_manager import NameManager

if TYPE_CHECKING:
    from collections.abc import Sequence

    from odoo.tools import SetDefinitions

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

MOVABLE_BRANDING = frozenset(
    {
        "data-oe-model",
        "data-oe-id",
        "data-oe-field",
        "data-oe-xpath",
        "data-oe-source-id",
    }
)
VIEW_MODIFIERS = ("column_invisible", "invisible", "readonly", "required")

CALENDAR_DATE_ATTRS = ("date_start", "date_delay", "date_stop", "color", "all_day")


_TEMPLATE_CACHE_FIELDS = frozenset(
    {
        "arch",
        "arch_base",
        "arch_db",
        "active",
        "inherit_id",
        "mode",
        "priority",
        "key",
        "model",
        "group_ids",
    }
)

_REVALIDATE_ALWAYS = frozenset({"active", "arch_db", "inherit_id"})
_REVALIDATE_ON_CHANGE = frozenset({"mode", "model", "priority", "type"})

_COMBINATION_ERRORS = (ValidationError, ValueError, etree.ParseError, TypeError)

_KEYS_WITH_COPIES = "ir.ui.view.keys_with_copies"
_CUSTOMIZED_VIEW_IDS = "ir.ui.view.customized_view_ids"

_CTE_EXCLUDED_FIELDS = frozenset(
    {
        "arch_prev",
        "arch_fs",
        "arch_updated",
        "create_uid",
        "create_date",
        "write_uid",
        "write_date",
    }
)


_VIEW_REF_RE = re.compile(
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


def hierarchy_views(hierarchy: dict[Any, list[Any]]) -> list[Any]:
    """Every overlay in a `_get_hierarchies()` tree, in no particular order."""
    return [view for children in hierarchy.values() for view in children]


def _hasclass(context: Any, *cls: str) -> bool:
    node_classes = set(context.context_node.attrib.get("class", "").split())
    return node_classes.issuperset(cls)


def _is_arch_absent(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value)


_IR_UI_VIEW_XMLID_SUFFIX = "_ir_ui_view"


def get_view_arch_from_file(filepath: str, xmlid: str) -> str | None:
    return _extract_view_arch(_parse_view_file(filepath), xmlid, filepath)


@functools.lru_cache(maxsize=256)
def _parse_cached(filepath: str, _mtime_ns: int, _size: int) -> etree._ElementTree:
    _debug.perf.count("view_file_parsed", path=filepath, size=_size)
    return etree.parse(filepath)


def _parse_view_file(filepath: str) -> etree._ElementTree:
    # dev-xml mode reads a view's file on every arch read, and a file holds
    # many views: parse it once per version. The tree is shared, so what is
    # read out of it is copied before it is edited.
    stat = Path(filepath).stat()
    return _parse_cached(filepath, stat.st_mtime_ns, stat.st_size)


def _iter_declarations(
    document: etree._ElementTree, candidate_ids: list[str]
) -> typing.Iterator[_Element]:
    for candidate in candidate_ids:
        for node in document.xpath("//*[@id=$id]", id=candidate):
            if node.tag in ("record", "template"):
                yield node


def _extract_view_arch(
    document: etree._ElementTree,
    xmlid: str,
    filepath: str,
    _seen: frozenset[str] = frozenset(),
) -> str | None:
    if xmlid in _seen:
        _logger.warning(
            "Cyclic view_id reference in file '%s': %s revisits '%s'",
            filepath,
            " -> ".join([*sorted(_seen), xmlid]),
            xmlid,
        )
        return None
    if "." not in xmlid:
        raise ValueError(f"Invalid xmlid {xmlid!r}: expected 'module.name' format")
    module, view_id = xmlid.split(".", 1)

    candidate_ids = [xmlid, view_id]
    if view_id.endswith(_IR_UI_VIEW_XMLID_SUFFIX):
        end = -len(_IR_UI_VIEW_XMLID_SUFFIX)
        candidate_ids += [xmlid[:end], view_id[:end]]

    for node in _iter_declarations(document, candidate_ids):
        node = copy.deepcopy(node)
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
                return _extract_view_arch(
                    document, ref_xmlid, filepath, _seen | {xmlid}
                )

            return None

        elif node.tag == "template":
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

_TRANSLATED_ATTRS_RE = re.compile(rf"@({'|'.join(TRANSLATED_ATTRS)})\b")
_WRONG_CLASS_RE = re.compile(r"(@class\s*=|=\s*@class|contains\(@class)")

_XML_ENCODING_DECL_RE = re.compile(r"<\?xml[^>]*encoding=.*?\?>", re.IGNORECASE)

_ARCH_FS_REF_RE = re.compile(r"(?<!%)%\((?P<xmlid>.*?)\)[ds]")


_QWEB_DIRECTIVES_ALLOWED = re.compile(r"t-translation")
_QWEB_DIRECTIVES_ALLOWED_TEMPLATE = re.compile(
    r"t-(?:translation|name|esc|out|set|value|if|else|elif|foreach|as|key|att|call|debug)"
)

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

    name = fields.Char(
        string="View Name",
        required=True,
    )
    model = fields.Char(index=True)
    key = fields.Char(index="btree_not_null")
    priority = fields.Integer(
        string="Sequence",
        default=16,
        required=True,
    )
    type = fields.Selection(
        selection=[
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
        string="View Architecture",
        compute="_compute_arch",
        inverse="_inverse_arch",
        help="""This field should be used when accessing view arch. It will use translation.
                               Note that it will read `arch_db` or `arch_fs` if in dev-xml mode.""",
    )
    arch_base = fields.Text(
        string="Base View Architecture",
        compute="_compute_arch_base",
        inverse="_inverse_arch_base",
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
        comodel_name="ir.ui.view",
        string="Inherited View",
        index=True,
        ondelete="restrict",
    )
    inherit_children_ids = fields.One2many(
        comodel_name="ir.ui.view",
        inverse_name="inherit_id",
        string="Views which inherit from this one",
    )
    model_data_id = fields.Many2one(
        comodel_name="ir.model.data",
        compute="_compute_model_data",
        search="_search_model_data_id",
    )
    xml_id = fields.Char(
        string="External ID",
        compute="_compute_model_data",
        help="ID of the view defined in xml file",
    )
    group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="ir_ui_view_group_rel",
        column1="view_id",
        column2="group_id",
        string="Groups",
        help="If this field is empty, the view applies to all users. Otherwise, the view applies to the users of those groups only.",
    )
    mode = fields.Selection(
        selection=[("primary", "Base view"), ("extension", "Extension View")],
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
        string="Warning information",
        compute="_compute_warning_info",
    )

    active = fields.Boolean(
        default=True,
        help="If this view is inherited,\n\n"
        "* if True, the view always extends its parent\n"
        "* if False, the view currently does not extend its parent but can be enabled",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model of the view",
        compute="_compute_model_id",
        inverse="_inverse_model_id",
    )

    invalid_locators = fields.Json(compute="_compute_invalid_locators")

    @api.depends("arch_db", "arch_fs", "arch_updated")
    @api.depends_context(
        "read_arch_from_file", "lang", "edit_translations", "check_translations"
    )
    def _compute_arch(self) -> None:
        read_from_file_ctx = self.env.context.get("read_arch_from_file")
        dev_xml = "xml" in config["dev_mode"]
        from_file = 0  # debuglog
        for view in self:
            arch_fs = None
            if read_from_file_ctx or (dev_xml and not view.arch_updated):
                arch_fs = view._get_arch_from_file()
            from_file += bool(arch_fs)  # debuglog
            view.arch = arch_fs or view.arch_db
        _debug.logic(
            "compute_arch",
            count=len(self),
            from_file=from_file,
            read_from_file_ctx=bool(read_from_file_ctx),
            dev_xml=dev_xml,
        )

    def _get_arch_from_file(self) -> str | None:
        self.check_singleton()
        if not self.arch_fs:
            return None
        xml_id = self.xml_id or self.key
        if not xml_id:
            return None

        try:
            arch = get_view_arch_from_file(
                file_path(self.arch_fs, check_exists=False), xml_id
            )
        except OSError:
            _logger.warning(
                "View %s: Full path [%s] cannot be found.", xml_id, self.arch_fs
            )
            _debug.logic("arch_file_unreadable", view=self.id, reason="missing")
            return None
        except etree.ParseError as e:
            _logger.warning(
                "View %s: file [%s] is not well-formed XML: %s", xml_id, self.arch_fs, e
            )
            _debug.logic("arch_file_unreadable", view=self.id, reason="parse")
            return None

        if not arch:
            _debug.logic("arch_file_unreadable", view=self.id, reason="not_found")
            return None
        _debug.logic(
            "arch_read_from_file", view=self.id, xml_id=xml_id, chars=len(arch)
        )
        return self._translate_arch_from_file(
            self._rewrite_arch_fs_refs(arch, xml_id).replace("%%", "%")
        )

    def _rewrite_arch_fs_refs(self, arch: str, xml_id: str) -> str:

        def replacer(m: re.Match[str]) -> str:
            ref = m.group("xmlid")
            if "." not in ref:
                ref = f"{xml_id.split('.', maxsplit=1)[0]}.{ref}"
            return str(self.env["ir.model.data"]._xmlid_to_res_id(ref))

        return _ARCH_FS_REF_RE.sub(replacer, arch)

    def _translate_arch_from_file(self, arch: str) -> str:
        lang = self.env.lang or "en_US"
        field_arch_db = self._fields["arch_db"]
        if lang == "en_US":
            # the file is the source language: the dictionary would map every
            # term to itself, and the walk is what normalises the arch
            return field_arch_db.translate(lambda term: term, arch)
        translations = field_arch_db.get_translation_dictionary(
            self.with_context(
                edit_translations=None, lang="en_US", check_translations=True
            ).arch_db,
            {lang: self.with_context(lang=lang, check_translations=True).arch_db},
        )
        return field_arch_db.translate(
            lambda term: translations.get(term, {}).get(lang), arch
        )

    def _inverse_arch(self) -> None:
        self._write_arch_db({view: view.arch for view in self})

    def _write_arch_db(self, arch_by_view: dict[Self, str]) -> None:
        # each view's arch_db is its own write, nested in the one that set
        # the arch: that write cleared the templates cache and dropped the
        # customizations already, and the set is validated once at the end,
        # so a tree several of them share combines once
        arch_fs = self._get_install_arch_fs()
        for view in self.with_context(ir_ui_view_nested_arch_write=True):
            arch = arch_by_view[view]
            self._check_xml_encoding(arch)
            data = {"arch_db": arch}
            if arch_fs:
                data["arch_fs"] = arch_fs
                data["arch_updated"] = False
            _debug.lifecycle("arch_written", view=view.id, arch_fs=arch_fs)
            view.write(data)
        self._check_xml()
        # xml_translate normalises what it stores, and the value depends on
        # the language: no environment keeps the value it was handed
        self.invalidate_recordset(["arch"])

    @api.depends("arch")
    @api.depends_context("read_arch_from_file")
    def _compute_arch_base(self) -> None:
        for view, view_wo_lang in zip(self, self.with_context(lang=None), strict=True):
            view.arch_base = view_wo_lang.arch

    def _inverse_arch_base(self) -> None:
        views_wo_lang = self.with_context(lang=None)
        views_wo_lang._write_arch_db(
            {
                view_wo_lang: view.arch_base
                for view, view_wo_lang in zip(self, views_wo_lang, strict=True)
            }
        )

    def reset_arch(self, mode: str = "soft") -> Self:
        reset = self.browse()
        for view in self:
            if mode == "soft":
                arch = view.arch_prev
                write_dict = {"arch_db": arch}
            elif mode == "hard":
                arch = view.with_context(lang=None)._get_arch_from_file()
                write_dict = {
                    "arch_db": arch,
                    "arch_prev": False,
                    "arch_updated": False,
                }
            else:
                _debug.logic("reset_arch_refused", view=view.id, mode=mode)
                raise ValueError(
                    f"reset_arch() got mode={mode!r}; expected 'soft' or 'hard'"
                )
            if not arch:
                _debug.logic("reset_arch_skipped", view=view.id, mode=mode)
                continue
            _debug.lifecycle("reset_arch", view=view.id, key=view.key, mode=mode)
            view.with_context(no_save_prev=True, lang=None).write(write_dict)
            reset += view
        return reset

    def _get_ir_model_data_rows(self) -> dict[int, list[dict[str, Any]]]:
        rows_by_view: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
        domain = [("model", "=", "ir.ui.view"), ("res_id", "in", self.ids)]
        for data in (
            self.env["ir.model.data"]
            .sudo()
            .search_read(domain, ["module", "name", "res_id"], order="id")
        ):
            rows_by_view[data["res_id"]].append(data)
        return rows_by_view

    @api.depends("write_date")
    def _compute_model_data(self) -> None:
        rows_by_view = self._get_ir_model_data_rows()
        _debug.perf.count(
            "model_data_rows", views=len(self), with_xmlid=len(rows_by_view)
        )
        for view in self:
            rows = rows_by_view.get(view.id)
            view.model_data_id = rows[0]["id"] if rows else False
            view.xml_id = f"{rows[0]['module']}.{rows[0]['name']}" if rows else ""

    def _search_model_data_id(
        self, operator: str, value: Any
    ) -> list[tuple[str, str, Any]] | types.NotImplementedType:
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

    def _inverse_model_id(self) -> None:
        for record in self:
            record.model = record.model_id.model

    @api.depends("arch", "inherit_id")
    def _compute_invalid_locators(self) -> None:
        self.invalid_locators = False
        for view in self:
            if not view.inherit_id or not view.arch:
                continue
            try:
                source = view.with_context(
                    ir_ui_view_tree_cut_off_view=view
                )._get_combined_arch()
                specs_tree = etree.fromstring(view.arch)
            except ValidationError, ValueError, etree.ParseError:
                _debug.logic("invalid_locators.broken_hierarchy", view=view.id)
                view.invalid_locators = [{"broken_hierarchy": True}]
                continue
            invalid_locators = list(view._iter_invalid_locators(source, specs_tree))
            _debug.logic(
                "invalid_locators", view=view.id, invalid=len(invalid_locators)
            )
            view.invalid_locators = invalid_locators or False

    def _iter_invalid_locators(
        self, source: _Element, specs_tree: _Element
    ) -> typing.Iterator[dict[str, Any]]:
        """Each spec of this overlay that names no node of ``source``, the
        specs applying as the walk goes so a later one sees what an earlier
        one inserted. A move inside a spec is a locator too; any other
        position on a spec's child is misplaced and reported as is."""

        def unlocated(spec: _Element) -> dict[str, Any] | None:
            node = None
            with suppress(ValidationError):
                node = self.locate_node(source, spec)
            if node is not None:
                return None
            return {
                "tag": spec.tag,
                "attrib": dict(spec.attrib),
                "sourceline": spec.sourceline,
            }

        specs = collections.deque([specs_tree])
        while specs:
            spec = specs.popleft()
            if isinstance(spec, etree._Comment):
                continue
            if spec.tag == "data":
                specs.extend(spec)
                continue
            if invalid := unlocated(spec):
                yield invalid
                continue
            inner_replace = spec.get("position") == "replace" and (
                spec.get("mode") == "inner"
            )
            for sub_spec in spec:
                sub_position = sub_spec.get("position")
                if sub_position == "move" and not inner_replace:
                    if invalid := unlocated(sub_spec):
                        yield invalid
                elif sub_position:
                    yield {
                        "tag": sub_spec.tag,
                        "attrib": dict(sub_spec.attrib),
                        "sourceline": sub_spec.sourceline,
                    }
            with suppress(ValueError, ValidationError):
                source = apply_inheritance_specs(source, spec)

    def _check_inheritance(self, arch: _Element) -> None:
        for node in _xpath_position(arch):
            if node.tag == "xpath":
                match = _TRANSLATED_ATTRS_RE.search(node.get("expr", ""))
                if match:
                    _debug.logic(
                        "inheritance_refused",
                        view=self.id,
                        attribute=match.group(1),
                        reason="translated_attr_in_xpath",
                    )
                    message = f"View inheritance may not use attribute {match.group(1)!r} as a selector."
                    raise self._prepare_view_error(message, node)
                if _WRONG_CLASS_RE.search(node.get("expr", "")):
                    _debug.logic(
                        "inheritance_warned", view=self.id, reason="class_in_xpath"
                    )
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
                        _debug.logic(
                            "inheritance_refused",
                            view=self.id,
                            attribute=attr,
                            reason="translated_attr_selector",
                        )
                        message = f"View inheritance may not use attribute {attr!r} as a selector."
                        raise self._prepare_view_error(message, node)

    def _get_combined_arch_checked(
        self, combined_archs: dict[int, _Element]
    ) -> _Element:
        self.check_singleton()
        if self.inherit_id:
            self._check_inheritance(etree.fromstring(self.arch or "<data/>"))
        if self.id in combined_archs:
            return combined_archs[self.id]
        return self._get_combined_arch()

    def _get_combined_archs_by_id(self) -> dict[int, _Element]:
        if len(self) < 2:
            _debug.logic("combined_archs_by_id.skipped", views=len(self))
            return {}
        try:
            return dict(zip(self.ids, self._get_combined_archs(), strict=True))
        except _COMBINATION_ERRORS as e:
            _debug.logic(
                "combined_archs_by_id.failed", views=len(self), error=type(e).__name__
            )
            return {}

    def _check_xml(self) -> bool:
        partial_validation = self.env.context.get("ir_ui_view_partial_validation")
        views = self.with_context(
            validate_view_ids=(self._ids if partial_validation else True)
        )

        combined_archs = views._get_combined_archs_by_id()
        _debug.pipeline(
            "check_xml",
            views=len(views),
            partial=bool(partial_validation),
            combined=len(combined_archs),
        )

        checked_roots: set[int] = set()
        for view in views:
            if partial_validation and not view.arch:
                _debug.logic("check_xml.skipped", view=view.id, reason="no_arch")
                continue
            try:
                combined_arch = view._get_combined_arch_checked(combined_archs)

                if view.inherit_id or view.inherit_children_ids:
                    root = view._get_primary_root()
                    if root.id not in checked_roots:
                        checked_roots.add(root.id)
                        root._check_sibling_primary_views()

                if view.type == "qweb":
                    _debug.logic("check_xml.skipped", view=view.id, reason="qweb")
                    continue
            except (etree.ParseError, ValueError, TypeError) as e:
                _debug.logic(
                    "check_xml.failed",
                    view=view.id,
                    stage="combine",
                    error=type(e).__name__,
                )
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
                view._check_combined_arch(combined_arch)
            except ValueError as e:
                _debug.logic(
                    "check_xml.failed",
                    view=view.id,
                    stage="validate",
                    error=type(e).__name__,
                )
                self._reraise_view_validation_error(e, view)

        return True

    def _check_combined_arch(self, combined_arch: _Element) -> None:
        """This non-qweb view's combined arch against the model and the
        schema; raises the ValueError _check_xml reports."""
        self.check_singleton()
        if _xpath_attrs(combined_arch) or _xpath_states(combined_arch):
            _debug.logic("check_xml.failed", view=self.id, stage="legacy_attrs")
            err = ValidationError(
                _(
                    'Since 17.0, the "attrs" and "states" attributes are no longer used.\nView: %(name)s in %(file)s',
                    name=self._view_display_name(),
                    file=self.arch_fs,
                )
            )
            err.context = {"name": "invalid view"}
            raise err

        with _debug.perf("check_view", cr=self.env.cr, view=self.id, model=self.model):
            self._check_view(combined_arch, self.model)

        view_archs = (
            list(combined_arch) if combined_arch.tag == "data" else [combined_arch]
        )
        _debug.pipeline("check_xml.schema", view=self.id, archs=len(view_archs))
        for view_arch in view_archs:
            for node in _xpath_validate(view_arch):
                del node.attrib["__validate__"]
            if not valid_view(view_arch, env=self.env, model=self.model):
                _debug.logic("check_xml.failed", view=self.id, stage="schema")
                raise ValidationError(
                    _(
                        "Invalid view %(name)s definition in %(file)s",
                        name=self._view_display_name(),
                        file=self.arch_fs,
                    )
                )

    def _reraise_view_validation_error(
        self, error: ValueError, view: Self
    ) -> typing.NoReturn:
        _debug.logic(
            "validation_error_reraised",
            view=view.id,
            with_context=hasattr(error, "context"),
            chained=error.__context__ is not None,
        )
        if hasattr(error, "context"):
            lines = etree.tostring(
                view._get_combined_arch(), encoding="unicode"
            ).splitlines(keepends=True)
            # a node built in code, not parsed, has no line: show the start
            line = error.context["line"] or 1
            fivelines = "".join(lines[max(0, line - 3) : line + 2])
            err = ValidationError(
                _(
                    "Error while validating view near:\n\n%(fivelines)s\n%(error)s",
                    fivelines=fivelines,
                    error=error,
                )
            )
            err.context = error.context
            raise err.with_traceback(error.__traceback__) from None
        if error.__context__:
            err = ValidationError(
                _(
                    "Error while validating view (%(view)s):\n\n%(error)s",
                    view=view.key or view.id,
                    error=error.__context__,
                )
            )
            err.context = {"name": "invalid view"}
            raise err.with_traceback(error.__context__.__traceback__) from None
        raise ValidationError(
            _(
                "Error while validating view (%(view)s):\n\n%(error)s",
                view=view.key or view.id,
                error=error,
            )
        ) from None

    def _get_primary_root(self) -> Self:
        self.check_singleton()
        root = self
        while root.inherit_id and root.mode != "primary":
            root = root.inherit_id
        return root

    def _check_sibling_primary_views(self) -> None:
        """The primary views hanging off these primary roots still combine:
        they inherit the roots' extensions and one may no longer apply."""
        # one read per level, none when the tree is in cache already
        sibling_primary_views = self.env["ir.ui.view"]
        level = self
        while level:
            children = level.inherit_children_ids
            primaries = children.filtered(lambda view: view.mode == "primary")
            sibling_primary_views |= primaries
            level = children - primaries

        if not self.pool.ready and sibling_primary_views and self.pool.loaded_modules:
            found = len(sibling_primary_views)  # debuglog
            sibling_primary_views = sibling_primary_views._filter_loaded_views(
                include_loaded_xmlids=True
            )
            _debug.logic(
                "sibling_primary_views_filtered",
                roots=self.ids,
                found=found,
                loaded=len(sibling_primary_views),
            )

        _debug.pipeline(
            "sibling_primary_views_checked",
            roots=self.ids,
            siblings=len(sibling_primary_views),
        )
        if sibling_primary_views:
            sibling_primary_views._get_combined_archs()

    @api.constrains("group_ids", "inherit_id", "mode")
    def _check_groups(self) -> None:
        for view in self:
            if view.group_ids and view.inherit_id and view.mode != "primary":
                _debug.logic("groups_on_extension_refused", view=view.id)
                raise ValidationError(
                    _(
                        "Inherited view cannot have 'Groups' define on the record. Use 'groups' attributes inside the view definition"
                    )
                )

    @api.constrains("inherit_id")
    def _check_000_inheritance(self) -> None:
        if self._has_cycle("inherit_id"):
            _debug.logic("inheritance_cycle", views=self.ids)
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

    def _default_mode(self, values: dict[str, Any]) -> dict[str, Any]:
        """The values with the mode an inherit_id change implies, when they
        set none: an extension under a parent, a primary without one. A view
        that already inherits keeps its mode when the parent changes."""
        if "mode" in values or "inherit_id" not in values:
            return values
        if values["inherit_id"] and self and all(view.inherit_id for view in self):
            return values
        mode = "extension" if values["inherit_id"] else "primary"
        _debug.logic(
            "mode_defaulted",
            views=len(self),
            inherit_id=values["inherit_id"] or None,
            mode=mode,
        )
        return {**values, "mode": mode}

    @api.depends("arch", "inherit_id", "type", "model")
    def _compute_warning_info(self) -> None:
        combined_archs = self._get_combined_archs_by_id()
        _debug.pipeline(
            "compute_warning_info", views=len(self), combined=len(combined_archs)
        )
        for view in self:
            view.warning_info = ""
            if not view.arch:
                continue
            try:
                combined_arch = view._get_combined_arch_checked(combined_archs)
                if view.type != "qweb":
                    name_manager = view._postprocess_view(
                        combined_arch, view.model, preserve_groups=True
                    )
                    view.warning_info = name_manager.warning
            except (etree.ParseError, ValueError, TypeError) as e:
                _debug.logic("warning_info.error", view=view.id, error=type(e).__name__)
                view.warning_info = str(e)

    def _group_inconsistency_warning(
        self, name_manager: NameManager, missing_fields: dict[str, Any]
    ) -> Markup:
        warning = Markup("")
        for name, (missing_groups, reasons) in missing_fields.items():
            error_message = name_manager._error_message_group_inconsistency(
                name, missing_groups, reasons
            )[0]
            if error_message:
                if warning:
                    warning += Markup("<br/>\n<br/>\n")
                warning += error_message.replace("\n", Markup("<br/>\n"))
        return warning

    def _check_xml_encoding(self, text: str | None) -> None:
        if isinstance(text, str) and _XML_ENCODING_DECL_RE.search(text):
            _debug.logic("xml_encoding_refused", views=len(self))
            raise UserError(
                _(
                    "Unicode strings with encoding declaration are not supported in XML.\n"
                    "Remove the encoding declaration."
                )
            )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        if not vals_list:
            return self.browse()
        vals_list = [dict(vals) for vals in vals_list]
        parent_types = self._get_parent_types(vals_list)
        for values in vals_list:
            self._prepare_view_create_values(values, parent_types)
        vals_list = [self._default_mode(values) for values in vals_list]
        self.env.registry.clear_cache("templates")
        result = super().create(vals_list)
        _debug.lifecycle(
            "create",
            count=len(result),
            inheriting=sum(1 for v in vals_list if v.get("inherit_id")),
            types=sorted({v.get("type") for v in vals_list if v.get("type")}),
        )
        result.with_context(ir_ui_view_partial_validation=True)._check_xml()
        return result

    def _get_parent_types(self, vals_list: list[dict[str, Any]]) -> dict[int, str]:
        """The type of each parent a typeless view in the batch inherits."""
        inherit_ids = {
            values["inherit_id"]
            for values in vals_list
            if values.get("inherit_id") and not values.get("type")
        }
        parent_types = (
            {parent.id: parent.type for parent in self.browse(inherit_ids)}
            if inherit_ids
            else {}
        )
        _debug.perf.count(
            "create.parent_types", count=len(vals_list), parents=len(parent_types)
        )
        return parent_types

    def _prepare_view_create_values(
        self, values: dict[str, Any], parent_types: dict[int, str]
    ) -> None:
        if "arch_db" in values and _is_arch_absent(values["arch_db"]):
            del values["arch_db"]
        for fname in ("arch", "arch_base", "arch_db"):
            self._check_xml_encoding(values.get(fname))

        if not values.get("type"):
            view_type = self._infer_view_type(values, parent_types)
            if view_type:
                values["type"] = view_type
        if not values.get("key") and values.get("type") == "qweb":
            values["key"] = f"gen_key.{str(uuid.uuid4())[:6]}"
            _debug.logic("create.key_generated", model=values.get("model"))
        if not values.get("name"):
            known = [part for part in (values.get("model"), values.get("type")) if part]
            values["name"] = " ".join(known) or _("Unnamed view")
        values["arch_prev"] = self._first_arch(values, ("arch_base", "arch_db", "arch"))
        if "arch" in values:
            values["arch_db"] = values.pop("arch")
            arch_fs = self._get_install_arch_fs()
            if arch_fs:
                values["arch_fs"] = arch_fs
                values["arch_updated"] = False
                _debug.logic(
                    "create.arch_fs_set", name=values.get("name"), arch_fs=arch_fs
                )

    @staticmethod
    def _first_arch(values: dict[str, Any], fnames: tuple[str, ...]) -> str | None:
        return next(
            (
                values[fname]
                for fname in fnames
                if fname in values and not _is_arch_absent(values[fname])
            ),
            None,
        )

    def _infer_view_type(
        self, values: dict[str, Any], parent_types: dict[int, str]
    ) -> str | None:
        """The type the values imply: the parent's, or the root tag of the
        arch. None when the arch does not parse -- validation reports that."""
        if values.get("inherit_id"):
            return parent_types.get(values["inherit_id"])
        arch = self._first_arch(values, ("arch", "arch_base", "arch_db"))
        if arch is None:
            _debug.logic("create.type_refused", reason="no_arch")
            raise ValidationError(_("Missing view architecture."))
        try:
            view_type = etree.fromstring(arch).tag
        except etree.ParseError, ValueError, TypeError:
            return None
        valid_types = self._get_view_type_tags()
        if view_type not in valid_types:
            _debug.logic("create.type_refused", type=view_type, reason="invalid_type")
            raise ValidationError(
                _(
                    "Invalid view type: '%(view_type)s'.\n"
                    "You might have used an invalid starting tag in the architecture.\n"
                    "Allowed types are: %(valid_types)s",
                    view_type=view_type,
                    valid_types=", ".join(sorted(valid_types)),
                )
            )
        return view_type

    def _get_install_arch_fs(self) -> str | None:
        """The addons-relative path of the data file being loaded, if any."""
        install_filename = self.env.context.get("install_filename")
        if not install_filename:
            return None
        path_info = get_resource_from_path(install_filename)
        return path_info.addons_path if path_info else None

    def write(self, vals: dict[str, Any]) -> bool:
        for fname in ("arch", "arch_base", "arch_db"):
            self._check_xml_encoding(vals.get(fname))
        if self._write_split_by_mode_default(vals):
            return True
        vals = self._with_arch_updated(vals)

        nested_arch_write = self.env.context.get("ir_ui_view_nested_arch_write")
        if not nested_arch_write and _TEMPLATE_CACHE_FIELDS.intersection(vals):
            self._forget_rendered_templates()
        if "arch_db" in vals and not self.env.context.get("no_save_prev"):
            self._save_arch_prev()

        revalidate = not _REVALIDATE_ALWAYS.isdisjoint(vals)
        recombines = not revalidate and self._is_recombination_required(vals)
        _debug.lifecycle(
            "write",
            count=len(self),
            fields=list(vals),
            revalidate=revalidate,
            recombines=recombines,
        )
        vals = self._default_mode(vals)
        if revalidate:
            return self._write_revalidating(vals, deferred=bool(nested_arch_write))
        if recombines:
            return self._write_recombining(vals)
        return super().write(vals)

    def _write_split_by_mode_default(self, vals: dict[str, Any]) -> bool:
        """The mode an inherit_id change implies is per view (_default_mode):
        a batch where some views already inherit and some do not is written
        as two. True when it was."""
        if "mode" in vals or not vals.get("inherit_id"):
            return False
        inheriting = self.filtered("inherit_id")
        if not inheriting or inheriting == self:
            return False
        _debug.logic(
            "write.split_by_mode_default",
            inheriting=len(inheriting),
            fresh=len(self - inheriting),
        )
        inheriting.write(vals)
        (self - inheriting).write(vals)
        return True

    def _with_arch_updated(self, vals: dict[str, Any]) -> dict[str, Any]:
        """An arch written outside a data file marks the view as modified."""
        if (
            "arch_updated" in vals
            or not ("arch" in vals or "arch_base" in vals)
            or "install_filename" in self.env.context
        ):
            return vals
        return {**vals, "arch_updated": True}

    def _forget_rendered_templates(self) -> None:
        """What a change to how these views render invalidates: the users'
        customizations of them and the registry-wide templates cache."""
        custom_view = self._get_customizations()
        _debug.lifecycle(
            "write.template_cache_cleared",
            views=len(self),
            custom_views=len(custom_view),
        )
        if custom_view:
            custom_view.unlink()
        self.env.registry.clear_cache("templates")

    def _save_arch_prev(self) -> None:
        saved = 0  # debuglog
        for view in self.with_context(lang=None):
            if view.arch_db:
                super(IrUiView, view).write({"arch_prev": view.arch_db})
                saved += 1  # debuglog
        _debug.lifecycle("write.arch_prev_saved", views=len(self), saved=saved)

    def _write_revalidating(self, vals: dict[str, Any], *, deferred: bool) -> bool:
        res = super().write(vals)
        if deferred:
            _debug.logic("write.validation_deferred", views=self.ids)
        else:
            self._check_xml()
        return res

    def _write_recombining(self, vals: dict[str, Any]) -> bool:
        # combine once on the written tree; only a tree that fails is asked
        # whether it combined before the write, and one that did not is
        # written without a verdict, the way a repair of a broken view needs
        try:
            with self.env.cr.savepoint():
                res = super().write(vals)
                self._check_xml()
        except _COMBINATION_ERRORS as error:
            combined_before = self._can_combine()
            _debug.logic(
                "recombination_failed",
                views=self.ids,
                error=type(error).__name__,
                combined_before=combined_before,
            )
            if combined_before:
                self._refuse_recombination(error)
            res = super().write(vals)
        return res

    def _get_customizations(self) -> Any:
        """The users' customizations of these views, which a write on what
        the view shows drops. While loading, the views that carry one are one
        query per pass: every view written from a data file asked its own."""
        Custom = self.env["ir.ui.view.custom"].sudo()
        if self.pool.is_loading:
            state = self.pool.loading.state(_CUSTOMIZED_VIEW_IDS, dict)
            if "ids" not in state:
                rows = self.env.execute_query(
                    SQL("SELECT DISTINCT ref_id FROM ir_ui_view_custom")
                )
                state["ids"] = {ref_id for (ref_id,) in rows}
                _debug.perf.count("customized_views_loaded", views=len(state["ids"]))
            if state["ids"].isdisjoint(self.ids):
                return Custom
        return Custom.search([("ref_id", "in", self.ids)])

    @api.model
    def _forget_customized_views(self) -> None:
        # a customization made while loading changes which views carry one
        if self.pool.is_loading:
            self.pool.loading.state(_CUSTOMIZED_VIEW_IDS, dict).clear()

    def _can_combine(self) -> bool:
        try:
            self._check_xml()
        except _COMBINATION_ERRORS as e:
            _debug.logic("can_combine", views=self.ids, error=type(e).__name__)
            return False
        return True

    def _refuse_recombination(self, error: Exception) -> None:
        if not self.env.context.get("ir_ui_view_loading_records"):
            raise error
        _logger.warning(
            "Loading records left view(s) %s unable to combine: %s",
            ", ".join(str(view.key or view.id) for view in self),
            error,
        )
        _debug.logic(
            "recombination_deferred", views=self.ids, error=type(error).__name__
        )

    def _is_recombination_required(self, vals: dict[str, Any]) -> bool:
        for fname in _REVALIDATE_ON_CHANGE.intersection(vals):
            if any(view[fname] != vals[fname] for view in self):
                _debug.logic("recombination_required", views=self.ids, field=fname)
                return True
        return False

    def unlink(self) -> bool:
        if not self:
            return True
        if self.env.context.get("_force_unlink", False) and self.inherit_children_ids:
            _debug.lifecycle(
                "unlink.children_forced",
                views=len(self),
                children=len(self.inherit_children_ids),
            )
            self.inherit_children_ids.unlink()
        self.env.registry.clear_cache("templates")
        candidates = self._view_modes_without_default()
        _debug.lifecycle("unlink", count=len(self), view_modes=len(candidates))
        res = super().unlink()
        self.env["ir.actions.act_window"]._remove_view_modes_without_views(candidates)
        return res

    def _view_modes_without_default(self) -> set[tuple[str, str]]:
        return {
            (view.model, view.type)
            for view in self
            if view.model in self.env
            and view.type
            and not hasattr(self.env[view.model], f"_get_default_{view.type}_view")
        }

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
        default = dict(default or {})
        has_default_without_key = "key" not in default
        vals_list = super().copy_data(default=default)
        rekeyed = 0  # debuglog
        for view, vals in zip(self, vals_list, strict=True):
            if view.key and has_default_without_key:
                vals["key"] = f"{view.key}_{str(uuid.uuid4())[:6]}"
                rekeyed += 1  # debuglog
        _debug.lifecycle("copy_data", count=len(self), rekeyed=rekeyed)
        return vals_list

    @api.model
    def default_view(self, model: str, view_type: str) -> int | bool:
        view_id = self.search(
            self._get_domain_default_view(model, view_type), limit=1
        ).id
        _debug.logic("default_view", model=model, view_type=view_type, view=view_id)
        return view_id

    @api.model
    def _get_domain_default_view(self, model: str, view_type: str) -> Domain:
        return Domain(
            [
                ("model", "=", model),
                ("type", "=", view_type),
                ("mode", "=", "primary"),
            ]
        )

    @api.model
    def _get_domain_inheriting_views(self) -> Domain:
        tree_cut_off_view = self.env.context.get("ir_ui_view_tree_cut_off_view")
        domain = Domain("active", "=", True)
        if tree_cut_off_view:
            _debug.logic("inheriting_domain.cut_off", view=tree_cut_off_view.id)
            return domain | Domain("id", "=", tree_cut_off_view.id)
        return domain

    @api.model
    def _get_loaded_view_ids(
        self, res_ids: Collection[int], modules: Collection[str]
    ) -> set[int]:
        self.env["ir.model.data"].flush_model(["model", "res_id", "module"])
        self.flush_model()
        view = SQL.identifier("view")
        with _debug.perf(
            "loaded_view_ids", cr=self.env.cr, views=len(res_ids), modules=len(modules)
        ):
            rows = self.env.execute_query(
                SQL(
                    "SELECT view.id FROM ir_ui_view view WHERE view.id = ANY(%s) AND (%s)",
                    list(res_ids),
                    self._get_sql_view_loaded(view, list(modules)),
                )
            )
        return {view_id for (view_id,) in rows}

    def _get_sql_view_loaded(self, view: SQL, modules: list[str]) -> SQL:
        return SQL(
            """EXISTS (
                SELECT 1 FROM ir_model_data data
                WHERE data.model = 'ir.ui.view'
                AND data.res_id = %s.id
                AND data.module = ANY(%s)
            )""",
            view,
            modules,
        )

    @api.model
    @tools.ormcache()
    def _get_fields_inheriting_views(self) -> list[str]:
        return [
            f.name
            for f in self._fields.values()
            if f.prefetch is True
            and not f.groups
            and f.name not in _CTE_EXCLUDED_FIELDS
        ]

    def _get_views_inheriting(self) -> Self:
        if not self.ids:
            return self.browse()
        domain = self._get_domain_inheriting_views()
        query = self._search(domain)
        if query.from_clause != SQL.identifier("ir_ui_view"):
            _debug.logic("views_inheriting_refused", reason="joined_from_clause")
            raise ValueError(
                "_get_domain_inheriting_views() must resolve against ir_ui_view alone: "
                "the recursive closure below inlines its WHERE clause and cannot carry a "
                f"join. Got: {query.from_clause}"
            )
        closure = self.env.backend.descendants(
            self,
            "inherit_id",
            self.ids,
            domain=domain,
            step_domain=Domain("mode", "=", "extension"),
            same_columns=("model",),
        )
        closure.order = self._order_to_sql("priority, id", closure)
        field_names = self._get_fields_inheriting_views()
        with _debug.perf("views_inheriting_fetch", cr=self.env.cr, roots=len(self.ids)):
            views = self._fetch_query(
                closure, [self._fields[name] for name in field_names]
            )
        _debug.perf.count("views_inheriting", roots=len(self.ids), rows=len(views))
        return views

    def _filter_loaded_views(
        self,
        check_view_ids: Collection[int] = (),
        include_loaded_xmlids: bool = False,
    ) -> Self:
        ids_to_check = [vid for vid in self.ids if vid not in check_view_ids]
        if not ids_to_check:
            _debug.logic("filter_loaded_views.skipped", views=len(self))
            return self
        install_module = self.env.context.get("install_module")
        loaded_modules = list(self.pool.loaded_modules)
        if install_module:
            loaded_modules.append(install_module)
        valid_view_ids = self._get_loaded_view_ids(ids_to_check, loaded_modules) | set(
            check_view_ids
        )
        if include_loaded_xmlids:
            valid_view_ids.update(
                id_
                for id_, xid in self.browse(
                    vid for vid in ids_to_check if vid not in valid_view_ids
                )
                .get_external_id()
                .items()
                if xid in self.pool.loaded_xmlids
            )
        _debug.logic(
            "filter_loaded_views",
            candidates=len(ids_to_check),
            kept=sum(1 for vid in self.ids if vid in valid_view_ids),
            install_module=install_module,
        )
        return self.browse(vid for vid in self.ids if vid in valid_view_ids)

    def _check_view_access(self) -> bool:
        self.check_singleton()
        if self.inherit_id and self.mode != "primary":
            _debug.logic(
                "view_access.delegated", view=self.id, parent=self.inherit_id.id
            )
            return self.inherit_id._check_view_access()
        if set(self.group_ids.ids) & set(self.env.user._get_group_ids()):
            _debug.logic("view_access.granted", view=self.id, uid=self.env.uid)
            return True
        _debug.logic(
            "view_access_denied",
            view=self.id,
            uid=self.env.uid,
            groups=self.group_ids.ids,
        )
        if self.group_ids:
            error = _(
                "View '%(name)s' accessible only to groups %(groups)s ",
                name=self._view_display_name(),
                groups=", ".join([g.name for g in self.group_ids]),
            )
        else:
            error = _("View '%(name)s' is private", name=self._view_display_name())
        raise AccessError(error)

    def _view_display_name(self) -> str:
        self.check_singleton()
        return f"{self.name} ({self.xml_id})" if self.xml_id else self.name

    def _view_error_context(self, node: _Element | None) -> dict[str, Any]:
        return {
            "view": self,
            "name": self.name if len(self) == 1 else None,
            "xmlid": self.env.context.get("install_xmlid") or self.xml_id,
            "view.model": self.model,
            "view.parent": self.inherit_id,
            "file": self.env.context.get("install_filename"),
            "line": node.sourceline if node is not None else 1,
        }

    def _prepare_view_error(
        self,
        message: str,
        node: _Element | None = None,
        *,
        from_traceback: Any = None,
    ) -> ValueError:
        err = ValueError(message).with_traceback(from_traceback)
        err.context = self._view_error_context(node)
        return err

    def _log_view_warning(self, message: str, node: _Element | None) -> None:
        _debug.logic("view_warning", view=self.id, model=self.model)
        _logger.warning(
            "%s\nView error context:\n%s",
            message,
            pprint.pformat(self._view_error_context(node)),
        )

    def locate_node(self, arch: _Element, spec: _Element) -> _Element | None:
        return locate_node(arch, spec)

    def inherit_branding(self, specs_tree: _Element) -> _Element:
        _debug.pipeline("inherit_branding", view=self.id, tag=specs_tree.tag)
        for node in specs_tree.iterchildren(tag=etree.Element):
            if node.tag in {"data", "xpath"} or node.get("position"):
                self.inherit_branding(node)
            elif node.get("t-field"):
                node.set("data-oe-xpath", node.getroottree().getpath(node))
                self.inherit_branding(node)
            else:
                node.set("data-oe-id", str(self.id))
                node.set("data-oe-xpath", node.getroottree().getpath(node))
                node.set("data-oe-model", "ir.ui.view")
                node.set("data-oe-field", "arch")
        return specs_tree

    def _validates_whole(self) -> bool:
        validate_view_ids = self.env.context.get("validate_view_ids")
        return bool(validate_view_ids) and (
            validate_view_ids is True or self.id in validate_view_ids
        )

    def _flag_validated_specs(self, arch: _Element) -> bool:
        """Mark what of this overlay's specs the validation covers: the nodes
        an after/before/inside spec inserts, the attributes spec's target.
        True when the overlay replaces a node, which validates the whole
        combined view — the caller flags its root."""
        validate_view_ids = self.env.context.get("validate_view_ids")
        if (
            not validate_view_ids
            or validate_view_ids is True
            or self.id not in validate_view_ids
        ):
            return False
        _debug.logic("validation_flagged", view=self.id, scope="specs")
        for node in _xpath_position(arch):
            position = node.get("position")
            if position in ("after", "before", "inside"):
                for child in node.iterchildren(tag=etree.Element):
                    if not child.get("position"):
                        child.set("__validate__", "1")
            elif position == "replace":
                return True
            elif position == "attributes":
                node.append(E.attribute("1", name="__validate__"))
        return False

    @api.model
    def apply_inheritance_specs(
        self, source: _Element, specs_tree: _Element
    ) -> _Element:
        try:
            source = apply_inheritance_specs(
                source,
                specs_tree,
                inherit_branding=self.env.context.get("inherit_branding"),
            )
        except ValueError as e:
            _debug.logic(
                "inheritance_specs_failed", view=self.id, error=type(e).__name__
            )
            raise self._prepare_view_error(str(e), specs_tree) from None
        return source

    def _combine(self, hierarchy: dict[Self, list[Self]]) -> _Element:
        return self._combine_tree(hierarchy)[0]

    def _combine_tree(
        self, hierarchy: dict[Self, list[Self]]
    ) -> tuple[_Element, Node | None]:
        """The combined arch, and the IR it was combined on — None on the XML
        path (branding), where the tree carries no provenance."""
        self.check_singleton()
        if self.mode != "primary":
            _debug.logic("combine_refused", view=self.id, mode=self.mode)
            raise ValueError(
                f"_combine() requires a primary view, got mode={self.mode!r}"
            )

        combined_arch = etree.fromstring(self.arch)
        if self.env.context.get("inherit_branding"):
            combined_arch.attrib.update(
                {
                    "data-oe-model": "ir.ui.view",
                    "data-oe-id": str(self.id),
                    "data-oe-field": "arch",
                }
            )
        validates_whole = self._validates_whole()

        queue = collections.deque(
            sorted(hierarchy[self], key=lambda v: v.mode == "primary")
        )
        tree_cut_off_view = self.env.context.get("ir_ui_view_tree_cut_off_view")
        # The overlays apply as id-addressed patches on the view IR; a spec
        # the ids cannot name goes through the XML combine, and so does every
        # spec while branding is on (the website editor reads the processing
        # instructions and data-oe-* marks the XML path leaves).
        branding = bool(self.env.context.get("inherit_branding"))
        combined = None if branding else Applied(root=from_arch(combined_arch))
        applied = patched = 0  # debuglog
        while queue:
            view = queue.popleft()
            if view == tree_cut_off_view:
                _debug.logic("combine.cut_off", root=self.id, view=view.id)
                break
            applied += 1  # debuglog
            arch = etree.fromstring(view.arch or "<data/>")
            if branding:
                view.inherit_branding(arch)
            validates_whole |= view._flag_validated_specs(arch)
            if combined is None:
                combined_arch = view.apply_inheritance_specs(combined_arch, arch)
            else:
                if view.mode == "primary":
                    # a primary child starts a view of its own: what it sets
                    # over its base is its definition, not a conflict
                    combined.managed.clear()
                patched += view._apply_overlay(combined, arch)  # debuglog

            for child_view in reversed(hierarchy[view]):
                if child_view.mode == "primary":
                    queue.append(child_view)
                else:
                    queue.appendleft(child_view)

        # the flag lands on the root the overlays leave, so a replaced root
        # is validated whole too
        if validates_whole:
            _debug.logic("validation_flagged", view=self.id, scope="whole")
            if combined is None:
                combined_arch.set("__validate__", "1")
            else:
                combined.root.attrs["__validate__"] = "1"
        if combined is None:
            _debug.pipeline("combine", root=self.id, key=self.key, applied=applied)
            return combined_arch, None
        if _debug.logic.enabled and combined.conflicts:
            _debug.logic(
                "combine.attribute_conflicts",
                root=self.id,
                conflicts=len(combined.conflicts),
                targets=[c.target for c in combined.conflicts],
                attributes=[c.attribute for c in combined.conflicts],
                origins=[c.origins for c in combined.conflicts],
            )
        _debug.pipeline(
            "combine", root=self.id, key=self.key, applied=applied, patched=patched
        )
        return to_arch(combined.root), combined.root

    def _apply_overlay(self, combined: Applied, arch: _Element) -> int:
        """This view's specs onto the IR: as patches where the ids name the
        target, the XML combine for the rest. Returns how many were patches."""
        # the record reference, not the xml id: a provenance that costs no
        # query per overlay (the xml id is one ir.model.data lookup each)
        origin = f"ir.ui.view,{self.id}"
        items = apply_specs(combined, arch, origin, self.apply_inheritance_specs)
        patches = sum(isinstance(item, Patch) for item in items)
        if patches < len(items):
            _debug.logic(
                "combine.xml_fallback",
                view=self.id,
                specs=len(items),
                fallbacks=len(items) - patches,
            )
        return patches

    def get_provenance(self) -> dict[str, dict[str, Any]]:
        """Which view put each node of this view's combined arch where it is.

        Keyed by the node's id (`odoo.tools.view_ir.identify`): the primary
        for what its own arch holds, the overlay that inserted the node
        otherwise, as ``{"view_id": int, "xml_id": str | None, "kind": str}``.
        Empty while branding is on — the XML combine carries no provenance.
        """
        self.check_singleton()
        self.browse().check_access("read")
        (root, hierarchy) = self._get_hierarchies()[0]
        _arch, combined = root._combine_tree(hierarchy)
        if combined is None:
            return {}
        origins = {
            f"ir.ui.view,{view.id}": {"view_id": view.id, "xml_id": view.xml_id or None}
            for view in [root, *hierarchy_views(hierarchy)]
        }
        primary = origins[f"ir.ui.view,{root.id}"]
        return {
            node_id: {**origins.get(node.origin or "", primary), "kind": node.kind}
            for node_id, node in identify(combined).items()
        }

    def get_combined_arch(self) -> str:
        return etree.tostring(self._get_combined_arch(), encoding="unicode")

    def _get_combined_arch(self) -> _Element:
        self.check_singleton()
        return self._get_combined_archs()[0]

    def _prefetch_ancestry(self) -> None:
        if not self.ids:
            return

        field = self._fields["inherit_id"]
        pending = self
        while pending:
            if any(not self.env.cache.contains(view, field) for view in pending):
                break
            pending = pending.inherit_id
        else:
            return

        rows = self.env.backend.ancestors(self, "inherit_id", self.ids)
        _debug.perf.count("ancestry_prefetched", views=len(self.ids), rows=len(rows))
        if not rows:
            return
        ids, inherit_ids = zip(*rows, strict=True)
        self._fields["inherit_id"]._insert_cache(self.browse(ids), inherit_ids)

    def _get_hierarchies(self) -> list[tuple[Self, dict[Self, list[Self]]]]:
        """For each view, its primary root and the overlay tree under it."""
        chains = self._get_ancestor_chains()
        roots = self.browse(chain[-1] for chain in chains)
        views = self.browse(unique(view_id for chain in chains for view_id in chain))

        check_view_ids = views.env.context.get("check_view_ids") or []
        views = views.with_context(check_view_ids=[*check_view_ids, *views.ids])
        all_tree_views = views._get_views_inheriting()
        admitted = all_tree_views._get_admitted_view_ids(chains, check_view_ids)
        _debug.pipeline(
            "combined_archs",
            requested=len(self),
            roots=len(roots),
            tree_views=len(all_tree_views),
        )

        children_views = collections.defaultdict(list)
        for view in all_tree_views:
            children_views[view.inherit_id].append(view)

        def get_hierarchy(
            root: Self,
            chain: list[int],
            _hierarchy: dict[Self, list[Self]] | None = None,
        ) -> dict[Self, list[Self]]:
            if _hierarchy is None:
                _hierarchy = collections.defaultdict(list)
            _hierarchy[root.inherit_id].append(root)
            for child in children_views[root]:
                if admitted is not None and (
                    child.id not in admitted and child.id not in chain
                ):
                    continue
                if child.id in chain or child.mode != "primary":
                    get_hierarchy(child, chain, _hierarchy)
            return _hierarchy

        roots = roots.with_prefetch(all_tree_views._prefetch_ids)
        return [
            (root, get_hierarchy(root, chain))
            for root, chain in zip(roots, chains, strict=True)
        ]

    def _get_ancestor_chains(self) -> list[list[int]]:
        """For each view, the ids from itself up to its root, root last."""
        self._prefetch_ancestry()
        chains = []
        for view in self:
            chain = [view.id]
            while view.inherit_id:
                view = view.inherit_id
                chain.append(view.id)
            chains.append(chain)
        return chains

    def _get_admitted_view_ids(
        self, chains: list[list[int]], check_view_ids: Collection[int]
    ) -> set[int] | None:
        """While loading, the views of this tree a combine may apply: those
        of loaded modules, plus each view's own chain (checked by the caller
        per chain). None once the registry is ready, or when every view is
        asked for -- nothing is filtered then."""
        if self.pool.ready or self.env.context.get("load_all_views"):
            return None
        # while loading, a tree holds the views of loaded modules and the
        # chain of the view being resolved -- each view its own chain, as if
        # resolved alone, so a batch admits no other view's ancestors. Only
        # a view that can be a child needs its module looked up: not a root,
        # not one every chain holds (admitted for every view)
        in_every_chain = set.intersection(*map(set, chains)) if chains else set()
        tree_root_ids = {view.id for view in self if not view.inherit_id}
        admitted = set(
            self._filter_loaded_views(
                set(check_view_ids) | in_every_chain | tree_root_ids
            ).ids
        )
        _debug.logic(
            "hierarchies.loaded_only", unfiltered=len(self), loaded=len(admitted)
        )
        return admitted

    def _get_combined_archs(self) -> list[_Element]:
        # views under one root share the hierarchy: combine it once and hand
        # each a copy, since a caller edits the arch it gets
        combined: dict[tuple[Any, ...], _Element] = {}
        archs = []
        for root, hierarchy in self._get_hierarchies():
            key = (
                root.id,
                tuple(
                    (parent.id, tuple(child.id for child in children))
                    for parent, children in hierarchy.items()
                ),
            )
            if key in combined:
                archs.append(copy.deepcopy(combined[key]))
            else:
                combined[key] = root._combine(hierarchy)
                archs.append(combined[key])
        _debug.perf.count("combine_batch", requested=len(archs), combined=len(combined))
        return archs

    def _get_view_refs(self, node: _Element) -> dict[str, str]:
        context = node.get("context")
        if not context:
            return {}
        return {
            m.group("view_type"): m.group("view_id")
            for m in _VIEW_REF_RE.finditer(context)
        }

    @api.model
    def _get_field_names_in_cached_template(self) -> list[str]:
        return ["id", "key", "active"]

    def _get_template_cache_keys_minimal(self) -> tuple[bool]:
        return (bool(self.env.context.get("active_test", True)),)

    @api.model
    @tools.ormcache(
        "id_or_xmlid",
        "isinstance(id_or_xmlid, str) and self._get_template_cache_keys_minimal()",
        cache="templates",
    )
    def _get_cached_template_info(
        self,
        id_or_xmlid: int | str,
        _view: Self | None = None,
        _error: Exception | None = None,
    ) -> frozendict:
        view = None
        error = False
        if _error is not None:
            error = _error
        elif _view is not None:
            view = _view
        elif isinstance(id_or_xmlid, int):
            view = self.sudo().browse(id_or_xmlid)
            try:
                _ = view.key
            except MissingError:
                _debug.logic("template_info.missing", ref=id_or_xmlid)
                view = None
                error = MissingError(
                    self.env._("Template not found: '%s'", id_or_xmlid)
                )
        else:
            preload = self.sudo()._preload_views([id_or_xmlid])
            if id_or_xmlid in preload:
                info = preload[id_or_xmlid]
                view = info["view"]
                error = info["error"]
            else:
                _debug.logic("template_info.not_preloaded", ref=id_or_xmlid)
                error = SyntaxError("Error compiling template")
        _debug.perf.count(
            "template_info_cached",
            ref=id_or_xmlid,
            view=view.id if view else None,
            error=type(error).__name__ if error else None,
        )
        info = {
            f: view[f] if view else None
            for f in self._get_field_names_in_cached_template()
        }
        info["error"] = error
        return frozendict(info)

    @api.model
    def _prepare_cached_template_error(self, error: Exception) -> Exception:
        return copy.copy(error)

    @api.model
    def _get_template_view(
        self, id_or_xmlid: int | str, raise_if_not_found: bool = True
    ) -> Self:
        info = self._get_cached_template_info(id_or_xmlid)
        if info["error"] and raise_if_not_found:
            _debug.logic(
                "template_view_refused",
                ref=id_or_xmlid,
                error=type(info["error"]).__name__,
            )
            raise self._prepare_cached_template_error(info["error"])
        return self.browse(info["id"])

    @api.model
    def _get_domain_template(self, xmlids: list[str]) -> Domain:
        return Domain("key", "in", xmlids)

    @api.model
    def _get_template_order(self) -> str:
        return "priority, id"

    @api.model
    def _get_views_by_ref(
        self, ids_or_xmlids: Sequence[int | str]
    ) -> dict[int | str, Self | Exception]:
        views_sudo = self.sudo().with_context(
            load_all_views=True, raise_if_not_found=True
        )

        ids, xmlids = partition(lambda v: isinstance(v, int), ids_or_xmlids)

        view_by_ref = {}
        if xmlids:
            field_names = [
                f.name for f in views_sudo._fields.values() if f.prefetch is True
            ]
            domain = Domain("id", "in", ids) | self._get_domain_template(xmlids)
            views = views_sudo.search_fetch(
                domain, field_names, order=self._get_template_order()
            )
        else:
            views = views_sudo.browse(ids)

        for view in views:
            try:
                key = view.key
            except MissingError:
                _debug.logic("views_by_ref.vanished", view=view.id)
                continue
            view_by_ref[view.id] = view
            if key and key not in view_by_ref:
                view_by_ref[key] = view

        missing_xmlids = [
            xmlid for xmlid in xmlids if "." in xmlid and xmlid not in view_by_ref
        ]
        _debug.perf.count(
            "views_by_ref",
            ids=len(ids),
            xmlids=len(xmlids),
            found=len(views),
            missing_xmlids=len(missing_xmlids),
        )
        if missing_xmlids:
            view_by_ref.update(views_sudo._get_views_by_xmlid(missing_xmlids))

        for key, view in view_by_ref.items():
            self._get_cached_template_info(key, _view=view)

        for ref in (*ids, *xmlids):
            if ref not in view_by_ref:
                _debug.logic("views_by_ref.missing", ref=ref)
                error = self._missing_template_error(ref)
                self._get_cached_template_info(ref, _error=error)
                view_by_ref[ref] = error
        return view_by_ref

    def _missing_template_error(self, ref: int | str) -> MissingError:
        if isinstance(ref, int):
            return MissingError(
                self.env._("Template does not exist or has been deleted: %s", ref)
            )
        return MissingError(self.env._("Template not found: '%s'", ref))

    def _get_views_by_xmlid(self, xmlids: list[str]) -> dict[int | str, Self]:
        """The views the xmlids name through ir.model.data, each under its
        id, its xmlid and, first come, its key."""
        domain = Domain.OR(
            Domain("model", "=", "ir.ui.view")
            & Domain("module", "=", module)
            & Domain("name", "=", name)
            for module, name in (xmlid.split(".", 1) for xmlid in xmlids)
        )
        model_data_records = self.env["ir.model.data"].sudo().search(domain)
        views = self.browse(model_data_records.mapped("res_id")).exists()
        _debug.logic(
            "views_by_ref.xmlid_fallback",
            xmlids=len(xmlids),
            model_data=len(model_data_records),
            views=len(views),
        )
        view_by_id = {view.id: view for view in views}
        view_by_ref: dict[int | str, Self] = {}
        for model_data in model_data_records:
            view = view_by_id.get(model_data.res_id)
            if view is None:
                continue
            view_by_ref[view.id] = view
            view_by_ref[f"{model_data.module}.{model_data.name}"] = view
            if view.key and view.key not in view_by_ref:
                view_by_ref[view.key] = view
        return view_by_ref

    @tools.ormcache(cache="templates")
    def _clear_preload_views_cache_if_needed(self) -> None:
        self.env.cr.cache.pop("_compile_batch_", None)

    def _preload_views(
        self, refs: Sequence[int | str]
    ) -> dict[int | str, dict[str, Any]]:
        self._clear_preload_views_cache_if_needed()

        cache_key = self.env["ir.qweb"]._get_template_cache_signature()

        compile_batch = self.env.cr.cache.setdefault("_compile_batch_", {}).setdefault(
            cache_key, {}
        )

        # isdecimal, not isdigit: "²" is a digit int() refuses
        refs = [
            int(ref) if isinstance(ref, int) or ref.isdecimal() else ref
            for ref in refs
            if ref
        ]
        missing_refs = [ref for ref in refs if ref not in compile_batch]
        _debug.logic("preload_views", refs=len(refs), missing=len(missing_refs))
        if not missing_refs:
            return compile_batch

        with _debug.perf(
            "preload_views_resolve", cr=self.env.cr, missing=len(missing_refs)
        ):
            unknown_views = self._get_views_by_ref(missing_refs)

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
                    "error": view,
                }

        return compile_batch

    def postprocess_and_fields(
        self, node: _Element, model: str | None = None, **options: Any
    ) -> tuple[str, dict[str, set[str]]]:
        if self:
            self.check_singleton()

        with _debug.perf(
            "postprocess_view",
            cr=self.env.cr,
            view=self.id,
            model=model or self.model,
            type=node.tag,
        ):
            name_manager = self._postprocess_view(node, model or self.model, **options)
        self._strip_arch_indentation(node)
        arch = etree.tostring(node, encoding="unicode")

        fields_by_model: dict[str, set[str]] = {}
        queue = collections.deque([name_manager])
        while queue:
            manager = queue.popleft()
            fields_by_model.setdefault(manager.model._name, set()).update(
                manager.available_fields
            )
            queue.extend(manager.children)

        _debug.pipeline(
            "postprocess_and_fields",
            view=self.id,
            models=len(fields_by_model),
            fields=sum(len(names) for names in fields_by_model.values()),
            arch_chars=len(arch),
        )
        return arch, fields_by_model

    @staticmethod
    def _strip_arch_indentation(node: _Element) -> None:
        for elem in node.iter():
            if elem.text and not elem.text.strip():
                elem.text = elem.text.replace("\t", "")
            if elem.tail and not elem.tail.strip():
                elem.tail = elem.tail.replace("\t", "")

    def _postprocess_access_rights(self, tree: _Element) -> _Element:
        removed, unwrapped = self._drop_inaccessible_nodes(tree)
        model_access = self._apply_model_access(tree)
        _debug.pipeline(
            "access_rights_applied",
            view=self.id,
            uid=self.env.uid,
            removed=removed,
            unwrapped=unwrapped,
            model_access=model_access,
        )
        return tree

    def _drop_inaccessible_nodes(self, tree: _Element) -> tuple[int, int]:
        """Remove every node whose groups the user is not in, keeping its
        tail; unwrap a bare <t> the user may see. Returns (removed,
        unwrapped)."""
        group_definitions = self.env["res.groups"]._get_group_definitions()
        user_group_ids = self.env.user._get_group_ids()

        @functools.cache
        def has_access(groups_key: str) -> bool:
            return group_definitions.from_key(groups_key).matches(user_group_ids)

        removed = unwrapped = 0
        for node in _xpath_groups_key(tree):
            parent = node.getparent()
            if has_access(node.attrib.pop("__groups_key__")):
                if node.tag == "t" and not node.attrib and parent is not None:
                    self._unwrap_node(node, parent)
                    unwrapped += 1
                continue
            if parent is None:
                _debug.logic(
                    "access_rights.root_refused", view=self.id, uid=self.env.uid
                )
                raise AccessError(
                    _(
                        "View '%(name)s' is restricted to groups the user does not belong to.",
                        name=self._view_display_name() if self else tree.tag,
                    )
                )
            tail = node.tail
            previous = node.getprevious()
            parent.remove(node)
            removed += 1
            if tail:
                if previous is not None:
                    previous.tail = (previous.tail or "") + tail
                else:
                    parent.text = (parent.text or "") + tail
        return removed, unwrapped

    def _apply_model_access(self, tree: _Element) -> int:
        """Stamp each node carrying model_access_rights with what the user
        may do on that model: can_create/can_write on a field, the
        create/delete/edit flags the view left unset on a root, and the
        group flags of a kanban grouped on a many2one. Returns the count."""
        count = 0
        for node in _xpath_model_access(tree):
            count += 1
            model = self.env[node.attrib.pop("model_access_rights")]
            if node.tag == "field":
                node.set("can_create", str(model.has_access("create")))
                node.set("can_write", str(model.has_access("write")))
                continue
            self._deny_missing_actions(
                node,
                model,
                (("create", "create"), ("delete", "unlink"), ("edit", "write")),
            )
            if node.tag == "kanban":
                group_by_field = model._fields.get(node.get("default_group_by"))
                if group_by_field and group_by_field.type == "many2one":
                    self._deny_missing_actions(
                        node,
                        model.env[group_by_field.comodel_name],
                        (
                            ("group_create", "create"),
                            ("group_delete", "unlink"),
                            ("group_edit", "write"),
                        ),
                    )
        return count

    @staticmethod
    def _deny_missing_actions(
        node: _Element, model: models.BaseModel, actions: tuple[tuple[str, str], ...]
    ) -> None:
        for action, operation in actions:
            if not node.get(action) and not model.has_access(operation):
                node.set(action, "False")

    @staticmethod
    def _unwrap_node(node: _Element, parent: _Element) -> None:
        children = list(node)
        preceding = node.getprevious()

        def push_text(text: str | None, before: _Element | None) -> None:
            if not text:
                return
            if before is not None:
                before.tail = (before.tail or "") + text
            else:
                parent.text = (parent.text or "") + text

        if children:
            push_text(node.text, preceding)
            anchor = node
            for child in children:
                anchor.addnext(child)
                anchor = child
            push_text(node.tail, children[-1])
        else:
            push_text((node.text or "") + (node.tail or ""), preceding)

        parent.remove(node)

    def _postprocess_debug_to_cache(self, tree: _Element) -> None:
        for node in _xpath_groups(tree):
            groups = split_refs(node.attrib.get("groups", ""))
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
        is_debug = self.env.user.has_group("base.group_no_one")
        hidden = 0  # debuglog
        for node in _xpath_debug(tree):
            debug = node.attrib.pop("__debug__") == "True"
            if debug != is_debug:
                node.attrib["invisible"] = "1"
                node.attrib["column_invisible"] = "1"
                hidden += 1  # debuglog
        _debug.logic("debug_nodes_applied", view=self.id, debug=is_debug, hidden=hidden)
        return tree

    def _init_view_processing(
        self,
        node: _Element,
        model_name: str,
        node_info: dict[str, Any] | None,
        *,
        translate: bool,
    ) -> tuple[NameManager, SetDefinitions, Any]:
        if model_name not in self.env:
            _debug.logic("view_processing_refused", view=self.id, model=model_name)
            raise self._prepare_view_error(
                _("Model not found: %(model)s", model=model_name), node
            )

        group_definitions = self.env["res.groups"]._get_group_definitions()

        model_groups = (
            node_info["model_groups"] if node_info else group_definitions.universe
        )
        parent_name_manager = node_info["name_manager"] if node_info else None

        model_groups &= self.env["ir.model.access"]._get_groups_with_access(model_name)

        model = self.env[model_name]
        if not translate:
            model = model.with_context(lang=None)

        name_manager = NameManager(
            model, parent=parent_name_manager, model_groups=model_groups
        )
        return name_manager, group_definitions, model_groups

    def _narrow_model_groups(self, node_info: dict[str, Any], field: Any) -> None:
        if field.groups:
            group_definitions = node_info["group_definitions"]
            node_info["model_groups"] &= group_definitions.parse(
                field.groups, raise_if_not_found=False
            )

    def _iter_arch_nodes(
        self,
        root: _Element,
        get_node_info: Callable[[_Element, dict[str, Any] | None], dict[str, Any]],
    ) -> typing.Iterator[tuple[_Element, dict[str, Any]]]:
        stack: list[tuple[_Element, dict[str, Any] | None]] = [(root, None)]
        while stack:
            node, parent_info = stack.pop()
            had_parent = node.getparent() is not None
            node_info = get_node_info(node, parent_info)
            yield node, node_info
            if had_parent and node.getparent() is None:
                continue
            stack.extend(
                (child, node_info)
                for child in reversed(node_info.get("children", node))
            )

    def _get_arch_scope(
        self,
        root: _Element,
        model_name: str,
        node_info: dict[str, Any] | None,
        *,
        translate: bool,
        editable: bool,
        root_extra: dict[str, Any] | None = None,
        scoped: dict[str, Any] | None = None,
        refine: Callable[[_Element, dict[str, Any]], None] | None = None,
    ) -> tuple[
        NameManager, Callable[[_Element, dict[str, Any] | None], dict[str, Any]]
    ]:
        name_manager, group_definitions, model_groups = self._init_view_processing(
            root, model_name, node_info, translate=translate
        )
        root_info = {
            "view_type": root.tag,
            "model_groups": model_groups,
            "name_manager": name_manager,
            "group_definitions": group_definitions,
            **(root_extra or {}),
        }
        initial = {
            "view_groups": (
                node_info["view_groups"] if node_info else group_definitions.universe
            ),
            "editable": editable,
            **(scoped or {}),
        }

        def get_node_info(
            node: _Element, parent_info: dict[str, Any] | None
        ) -> dict[str, Any]:
            inherited = initial if parent_info is None else parent_info
            info = dict(root_info, **{key: inherited[key] for key in initial})
            info["editable"] = inherited["editable"] and self._editable_node(
                node, name_manager
            )
            if refine is not None:
                refine(node, info)
            if groups := node.get("groups"):
                info["view_groups"] &= group_definitions.parse(
                    groups, raise_if_not_found=False
                )
            return info

        return name_manager, get_node_info

    def _postprocess_view(
        self,
        node: _Element,
        model_name: str,
        editable: bool = True,
        node_info: dict[str, Any] | None = None,
        **options: Any,
    ) -> NameManager:
        root = node

        name_manager, get_node_info = self._get_arch_scope(
            root,
            model_name,
            node_info,
            translate=True,
            editable=editable,
            root_extra={"mobile": options.get("mobile")},
        )
        model = name_manager.model
        root_model_groups = name_manager.model_groups

        preserve_groups = options.get("preserve_groups")

        self._postprocess_debug_to_cache(root)

        nodes = grouped = 0  # debuglog
        for elem, elem_info in self._iter_arch_nodes(root, get_node_info):
            nodes += 1  # debuglog
            handler = ELEMENT_HANDLERS.get(elem.tag)
            if handler is not None:
                had_parent = elem.getparent() is not None
                handler.postprocess(self, elem, name_manager, elem_info)
                if had_parent and elem.getparent() is None:
                    continue

            elem_groups = elem.get("groups")
            if elem_groups or root_model_groups != elem_info["model_groups"]:
                groups = elem_info["model_groups"] & elem_info["view_groups"]
                elem.set("__groups_key__", groups.key)
                grouped += 1  # debuglog

            self._postprocess_attributes(elem, name_manager, elem_info)

            if elem_groups and preserve_groups:
                elem.attrib["groups"] = elem_groups

        missing_fields = self._add_missing_fields(root, name_manager)
        _debug.pipeline(
            "postprocess_view",
            view=self.id,
            model=model._name,
            view_type=root.tag,
            nodes=nodes,
            grouped=grouped,
            missing_fields=len(missing_fields),
            preserve_groups=bool(preserve_groups),
        )

        if preserve_groups:
            name_manager.warning = self._group_inconsistency_warning(
                name_manager, missing_fields
            )

        name_manager.update_available_fields()

        root.set("model_access_rights", model._name)

        if self._can_onchange_view(root):
            self._postprocess_on_change(root, model)

        return name_manager

    def _add_missing_fields(
        self, root: _Element, name_manager: NameManager
    ) -> dict[str, Any]:
        missing_fields = name_manager.get_fields_missing()
        for name, (missing_groups, reasons) in missing_fields.items():
            if name not in name_manager.field_info:
                _debug.logic(
                    "missing_field.unknown",
                    view=self.id,
                    model=name_manager.model._name,
                    field=name,
                )
                continue

            name_manager.available_fields[name].setdefault("info", {})
            name_manager.available_fields[name].setdefault("groups", []).append(
                missing_groups
            )
            name_manager.available_names.add(name)

            readonly = True
            if filename_reasons := [r for r in reasons if r[1][0] == "filename"]:
                filename_node = filename_reasons[-1][2]
                if node_readonly := filename_node.get("readonly"):
                    readonly = node_readonly
                else:
                    field = name_manager.model._fields[filename_node.get("name")]
                    if field.type == "binary":
                        readonly = field.readonly or False
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
            _debug.logic(
                "missing_field.added",
                view=self.id,
                model=name_manager.model._name,
                field=name,
                readonly=readonly,
                grouped="__groups_key__" in attrs,
            )
        return missing_fields

    def _postprocess_on_change(self, arch: _Element, model: models.BaseModel) -> None:
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

        flagged = 0  # debuglog
        for field, nodes in field_nodes.items():
            model = self.env[field.model_name]
            if model._has_onchange(field, field_nodes):
                flagged += 1  # debuglog
                for node in nodes:
                    if not node.get("on_change"):
                        node.set("on_change", "1")
        _debug.pipeline(
            "onchange_flagged", view=self.id, fields=len(field_nodes), flagged=flagged
        )

    def _get_x2many_missing_view_archs(
        self, field: Any, field_node: _Element, node_info: dict[str, Any]
    ) -> list[_Element]:
        current_view_types = [el.tag for el in _xpath_descendant_field(field_node)]
        declared_mode = field_node.get("mode")
        wanted = declared_mode.split(",") if declared_mode else ["kanban", "list"]
        if any(view_type in current_view_types for view_type in wanted):
            return []
        missing_view_types = [
            wanted[0]
            if declared_mode
            else ("kanban" if node_info.get("mobile") else "list")
        ]
        _debug.logic(
            "x2many_subview_missing",
            view=self.id,
            field=field.name,
            comodel=field.comodel_name,
            present=current_view_types,
            wanted=missing_view_types,
            mobile=bool(node_info.get("mobile")),
        )

        comodel = self.env[field.comodel_name].sudo(False)
        refs = self._get_view_refs(field_node)
        comodel = comodel.with_context(
            **{
                f"{view_type}_view_ref": refs.get(f"{view_type}_view_ref")
                for view_type in missing_view_types
            }
        )

        return [
            comodel._get_view(view_type=view_type)[0]
            for view_type in missing_view_types
        ]

    def _postprocess_attributes(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        for attr, expr in node.items():
            if attr in VIEW_MODIFIERS or attr.startswith("decoration-"):
                vnames = get_expression_field_names(expr)
                name_manager.add_used_fields(node, vnames, node_info, (attr, expr))
            elif attr == "groups":
                node.attrib.pop("groups")

    def _get_calendar_field_names(self, node: _Element) -> typing.Iterator[str | None]:
        for attr in CALENDAR_DATE_ATTRS:
            if value := node.get(attr):
                yield value.split(".", 1)[0]
        if aggregate := node.get("aggregate"):
            yield aggregate.split(":")[0]
        for child in node:
            if child.tag == "filter":
                yield child.get("name")

    def _add_available_calendar_fields(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        for name in self._get_calendar_field_names(node):
            name_manager.add_available_field(node, name, node_info)

    @api.model
    @tools.ormcache()
    def _get_view_type_tags(self) -> frozenset[str]:
        return frozenset(value for value, _label in self._fields["type"].selection)

    def _editable_node(self, node: _Element, name_manager: NameManager) -> bool:
        handler = ELEMENT_HANDLERS.get(node.tag)
        if handler is not None:
            answer = handler.editable(self, node, name_manager)
            if answer is not None:
                return answer
        return node.tag not in self._get_view_type_tags()

    def _can_onchange_view(self, node: _Element) -> bool | None:
        handler = ELEMENT_HANDLERS.get(node.tag)
        if handler is not None:
            return handler.can_onchange(self, node)
        return None

    def _check_view(
        self,
        node: _Element,
        model_name: str,
        view_type: str | None = None,
        editable: bool = True,
        node_info: dict[str, Any] | None = None,
    ) -> NameManager:
        self.check_singleton()

        view_type = view_type or self.type
        if not view_type:
            _debug.logic("check_view.refused", view=self.id, reason="no_view_type")
            raise self._prepare_view_error(
                _(
                    "The view type could not be determined from its architecture. "
                    "Check that the architecture is well-formed XML, or set the "
                    "view's type explicitly."
                ),
                node,
            )
        if node.tag != view_type:
            _debug.logic(
                "check_view.refused",
                view=self.id,
                view_type=view_type,
                tag=node.tag,
                reason="root_tag_mismatch",
            )
            raise self._prepare_view_error(
                _(
                    "The root node of a %(view_type)s view should be a <%(view_type)s>, not a <%(tag)s>",
                    view_type=view_type,
                    tag=node.tag,
                ),
                node,
            )
        if node_info is None and node.get("groups"):
            _debug.logic("check_view.refused", view=self.id, reason="groups_on_root")
            raise self._prepare_view_error(
                _(
                    "The root node of a view cannot carry a 'groups' attribute: "
                    "restricting it would leave nothing to display. Use the view's "
                    "'Groups' field (group_ids) to restrict the whole view, or move "
                    "the attribute onto the elements it should hide."
                ),
                node,
            )

        def refine(elem: _Element, info: dict[str, Any]) -> None:
            info["validate"] = info["validate"] or elem.get("__validate__")
            if groups := elem.get("groups"):
                for group_name in split_refs(groups.replace("!", "")):
                    name_manager.add_required_group(group_name, elem)

        name_manager, get_node_info = self._get_arch_scope(
            node,
            model_name,
            node_info,
            translate=False,
            editable=editable,
            scoped={"validate": node_info["validate"] if node_info else False},
            refine=refine,
        )

        nodes = validated = 0  # debuglog
        for elem, elem_info in self._iter_arch_nodes(node, get_node_info):
            nodes += 1  # debuglog
            handler = ELEMENT_HANDLERS.get(elem.tag)
            if handler is not None:
                handler.check(self, elem, name_manager, elem_info)

            if elem_info["validate"]:
                validated += 1  # debuglog
                self._check_attributes(elem, name_manager, elem_info)

        _debug.pipeline(
            "check_view",
            view=self.id,
            model=model_name,
            view_type=view_type,
            nodes=nodes,
            validated=validated,
            nested=node_info is not None,
        )
        name_manager.check(self)

        return name_manager

    def _check_subview_schema(self, subview: _Element, model_name: str) -> None:
        for elem in subview.iter(etree.Element):
            elem.attrib.pop("__validate__", None)
        if not valid_view(subview, env=self.env, model=model_name):
            _debug.logic(
                "subview_schema_refused",
                view=self.id,
                model=model_name,
                tag=subview.tag,
            )
            raise self._prepare_view_error(
                _("Invalid <%(tag)s> subview definition", tag=subview.tag), subview
            )

    def _get_client_button_types(self, view_type: str) -> set[str]:
        types = set()
        if self._is_qweb_based_view(view_type):
            types.update(
                ("open", "archive", "unarchive", "delete", "set_cover", "button")
            )
        if view_type in ("list", "groupby"):
            types.add("edit")
        return types

    def _check_dropdown_menu(self, node: _Element) -> None:
        for msg in get_dropdown_menu_warnings(node):
            self._log_view_warning(msg, node)

    def _check_progress_bar(self, node: _Element) -> None:
        for msg in get_progress_bar_warnings(node):
            self._log_view_warning(msg, node)

    def _is_qweb_based_view(self, view_type: str) -> bool:
        return view_type == "kanban"

    def _check_attributes(
        self,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        for attr in VIEW_MODIFIERS:
            py_expression = node.attrib.get(attr)
            if py_expression:
                self._check_expression(
                    node,
                    name_manager,
                    py_expression,
                    attr,
                    node_info,
                )

        for attr, expr in node.items():
            checker = attribute_check_for(attr)
            if checker is not None:
                checker.check(self, node, name_manager, attr, expr, node_info)

    def _check_classes(self, node: _Element, expr: str) -> None:
        for msg in get_class_accessibility_warnings(node, expr):
            self._log_view_warning(msg, node)

    def _check_fa_class_accessibility(self, node: _Element, description: str) -> None:
        for msg in get_fa_class_accessibility_warnings(node, description):
            self._log_view_warning(msg, node)

    def _check_qweb_directive(
        self, node: _Element, directive: str, view_type: str
    ) -> None:
        allowed = (
            _QWEB_DIRECTIVES_ALLOWED_TEMPLATE
            if self._is_qweb_based_view(view_type)
            else _QWEB_DIRECTIVES_ALLOWED
        )
        if not allowed.match(directive):
            _debug.logic(
                "qweb_directive_refused",
                view=self.id,
                directive=directive,
                view_type=view_type,
            )
            raise self._prepare_view_error(
                _("Forbidden owl directive used in arch (%s).", directive), node
            )

    def _check_expression(
        self,
        node: _Element,
        name_manager: NameManager,
        py_expression: str,
        attr: str,
        node_info: dict[str, Any],
    ) -> None:
        try:
            if py_expression.lower() in ("0", "false", "1", "true"):
                return
            fnames = get_expression_field_names(py_expression)
        except (SyntaxError, ValueError, AttributeError) as e:
            _debug.logic(
                "expression_refused",
                view=self.id,
                attribute=attr,
                error=type(e).__name__,
            )
            msg = _(
                "Invalid %(use)s: “%(expr)s”\n%(error)s",
                use=f"modifier {attr!r}",
                expr=py_expression,
                error=e,
            )
            raise self._prepare_view_error(msg, node) from e
        name_manager.add_used_fields(node, fnames, node_info, (attr, py_expression))

    def _check_domain_identifiers(
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
            _debug.logic(
                "domain_refused",
                view=self.id,
                model=target_model,
                error=type(e).__name__,
            )
            msg = _(
                "Invalid %(use)s: “%(expr)s”\n%(error)s",
                use=use,
                expr=domain,
                error=e,
            )
            raise self._prepare_view_error(msg, node) from e

        self._check_field_paths(node, fnames, target_model, f"{use} ({domain})")
        name_manager.add_used_fields(node, vnames, node_info, ("domain", domain))

    def _check_field_paths(
        self, node: _Element, field_paths: set[str], model_name: str, use: str
    ) -> None:
        root_model = self.pool[model_name]
        for field_path in field_paths:
            names = field_path.split(".")
            if names[0] == "parent":
                continue
            Model = root_model
            for index, name in enumerate(names):
                if Model is None:
                    _debug.logic(
                        "field_path_refused",
                        view=self.id,
                        path=field_path,
                        reason="non_relational",
                    )
                    msg = _(
                        "Non-relational field “%(field)s” in path “%(field_path)s” in %(use)s)",
                        field=names[index - 1],
                        field_path=field_path,
                        use=use,
                    )
                    raise self._prepare_view_error(msg, node)
                try:
                    field = Model._fields[name]
                except KeyError:
                    _debug.logic(
                        "field_path_refused",
                        view=self.id,
                        model=Model._name,
                        path=field_path,
                        reason="unknown_field",
                    )
                    msg = _(
                        'Unknown field "%(model)s.%(field)s" in %(use)s)',
                        model=Model._name,
                        field=name,
                        use=use,
                    )
                    raise self._prepare_view_error(msg, node) from None
                if not field._description_searchable:
                    _debug.logic(
                        "field_path_refused",
                        view=self.id,
                        model=Model._name,
                        path=field_path,
                        reason="unsearchable",
                    )
                    msg = _(
                        "Unsearchable field “%(field)s” in path “%(field_path)s” in %(use)s)",
                        field=name,
                        field_path=field_path,
                        use=use,
                    )
                    raise self._prepare_view_error(msg, node)
                if (
                    field.type in ("date", "datetime")
                    and index + 2 == len(names)
                    and names[-1] in models.READ_GROUP_NUMBER_GRANULARITY
                ):
                    break
                Model = self.pool.get(field.comodel_name)

    def _get_view_etrees(self) -> list[_Element]:
        if not self:
            return []
        arch_trees = self._get_combined_archs()
        with _debug.perf("distribute_branding", views=len(self), archs=len(arch_trees)):
            for arch_tree in arch_trees:
                self.distribute_branding(arch_tree)
        return arch_trees

    def _is_subtree_branded(self, node: _Element) -> bool:
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
            for descendant in e.iterdescendants(tag=etree.Element):
                if not MOVABLE_BRANDING.intersection(descendant.attrib):
                    continue
                self._pop_view_branding(descendant)

            for descendant in e.iterdescendants(tag=etree.ProcessingInstruction):
                if descendant.target == "apply-inheritance-specs-node-removal":
                    descendant.getparent().remove(descendant)
            return

        node_path = e.get("data-oe-xpath")
        if node_path is None:
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
            self._pop_view_branding(e)
        elif self._is_subtree_branded(e):
            distributed_branding = self._pop_view_branding(e)

            if "t-raw" not in e.attrib:
                indexes = collections.defaultdict(lambda: 0)
                for child in e.iterchildren(etree.Element, etree.ProcessingInstruction):
                    if child.get("data-oe-xpath"):
                        self.distribute_branding(child)
                    elif child.tag is etree.ProcessingInstruction:
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
        self._get_template_view(template).sudo()._check_view_access()
        _debug.pipeline("render_public_asset", template=template, uid=self.env.uid)
        return self.env["ir.qweb"].sudo()._render(template, values)

    def _render_template(
        self, template: int | str, values: dict[str, Any] | None = None
    ) -> Markup:
        return self.env["ir.qweb"]._render(template, values)

    @api.model
    def _get_domain_shipping_modules(self) -> Domain:
        """The modules whose xmlid makes a view shipped, not custom."""
        return Domain.TRUE

    @api.model
    def _get_custom_views(self, models: Collection[str] | None = None) -> Self:
        """The latest custom view of each model under each inheritance root,
        over ``models`` or every model: a custom view is one no module ships
        — no xmlid, or an xmlid whose module is not one the database knows."""
        domain = Domain("active", "=", True)
        if models is not None:
            domain &= Domain("model", "in", list(models))
        views = self.sudo().search_fetch(domain, ["model", "inherit_id"])
        shipping_modules = (
            self.env["ir.module.module"]
            .sudo()
            ._search(self._get_domain_shipping_modules())
        )
        shipped_ids = {
            data.res_id
            for data in self.env["ir.model.data"]
            .sudo()
            .search_fetch(
                [
                    ("model", "=", "ir.ui.view"),
                    ("res_id", "in", views.ids),
                    ("module", "in", shipping_modules.subselect("name")),
                ],
                ["res_id"],
            )
        }
        # a root's tree spans models (a primary of another model may hang off
        # it), and each model's custom views are checked on their own
        latest_by_root: dict[tuple[str | None, int], int] = {}
        for view in views:
            if view.id in shipped_ids:
                continue
            root = (view.model, view.inherit_id.id or view.id)
            latest_by_root[root] = max(latest_by_root.get(root, 0), view.id)
        custom = self.browse(sorted(latest_by_root.values()))
        _debug.perf.count(
            "custom_views_scanned",
            models=len(models) if models is not None else None,
            views=len(views),
            shipped=len(shipped_ids),
            custom=len(custom),
        )
        return custom

    @api.model
    def _check_module_views(self, module: str) -> None:
        if self.pool.ready:
            _debug.logic("module_views_check_refused", module=module, reason="ready")
            msg = (
                "_check_module_views() must only be called during module initialization"
            )
            raise RuntimeError(msg)

        prefix = module + "."
        prefix_len = len(prefix)
        names = [
            xmlid[prefix_len:]
            for xmlid in self.pool.loaded_xmlids
            if xmlid.startswith(prefix)
        ]
        if not names:
            _debug.logic(
                "module_views_check_skipped", module=module, reason="no_xmlids"
            )
            return

        views = self.browse(
            self.env["ir.model.data"]
            .sudo()
            .search_fetch(
                [
                    ("model", "=", "ir.ui.view"),
                    ("module", "=", module),
                    ("name", "in", names),
                    ("noupdate", "=", True),
                ],
                ["res_id"],
            )
            .mapped("res_id")
        )

        _debug.pipeline(
            "module_views_check", module=module, xmlids=len(names), views=len(views)
        )
        views._check_xml()

    def _create_all_specific_views(self, processed_modules: list[str]) -> None:
        if self.pool.is_loading:
            self.pool.loading.state(_KEYS_WITH_COPIES, dict).clear()

    def _get_keys_with_copies(self) -> set[str]:
        state = self.pool.loading.state(_KEYS_WITH_COPIES, dict)
        if "keys" not in state:
            rows = self.env.execute_query(
                SQL(
                    "SELECT key FROM ir_ui_view WHERE key IS NOT NULL "
                    "GROUP BY key HAVING count(*) > 1"
                )
            )
            state["keys"] = {key for (key,) in rows}
            _debug.perf.count("keys_with_copies_loaded", keys=len(state["keys"]))
        return state["keys"]

    def _get_views_specific(self) -> Self:
        self.check_singleton()
        if self.type != "qweb":
            return self.env["ir.ui.view"]
        if self.pool.is_loading and self.key not in self._get_keys_with_copies():
            _debug.logic("views_specific.none", view=self.id, key=self.key)
            return self.env["ir.ui.view"]
        specific = (
            self.with_context(active_test=False)
            .search([("key", "=", self.key)])
            .filtered(lambda r: r.xml_id != r.key)
        )
        _debug.perf.count(
            "views_specific", view=self.id, key=self.key, specific=len(specific)
        )
        return specific

    def _load_records_write(self, values: dict[str, Any]) -> None:
        view = self.with_context(ir_ui_view_loading_records=True)
        if view.type == "qweb":
            cow_views = view._get_views_specific()
            _debug.pipeline(
                "load_records_write_cow",
                view=view.id,
                key=view.key,
                specific=len(cow_views),
                fields=list(values),
            )
            for cow_view in cow_views:
                authorized_vals = {
                    key: value
                    for key, value in values.items()
                    if key != "inherit_id" and cow_view[key] == view[key]
                }
                inherit_id = values.get("inherit_id")
                if (
                    inherit_id
                    and view.inherit_id.id != inherit_id
                    and cow_view.inherit_id.key == view.inherit_id.key
                ):
                    view._load_records_write_on_cow(
                        cow_view, inherit_id, authorized_vals
                    )
                else:
                    _debug.lifecycle(
                        "cow_view_written",
                        cow_view=cow_view.id,
                        fields=list(authorized_vals),
                    )
                    cow_view.with_context(no_cow=True).write(authorized_vals)
        super(IrUiView, view)._load_records_write(values)

    def _load_records_write_on_cow(
        self, cow_view: Self, inherit_id: int, values: dict[str, Any]
    ) -> None:
        _debug.lifecycle(
            "cow_view_deferred", cow_view=cow_view.id, inherit_id=inherit_id
        )
        self.pool.loading.state("ir.ui.view.cow_views_to_adapt", list).append(
            (
                cow_view.id,
                inherit_id,
                values,
            )
        )
