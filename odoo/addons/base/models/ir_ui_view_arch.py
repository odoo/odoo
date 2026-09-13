from __future__ import annotations

import annotationlib
import ast
import inspect
import re
from typing import Any

from lxml import etree
from lxml.builder import E
from lxml.etree import _Element

from odoo.tools import _
from odoo.tools.view_validation import (
    att_names,
    get_dict_asts,
    get_expression_field_names,
)

from .ir_ui_view_name_manager import NameManager

_NESTED_VIEW_TAGS = frozenset({"form", "list", "graph", "kanban", "calendar"})

COMP_REGEX = re.compile(r"(^|[^\w])\s*__comp__\s*([^\w]|$)")

_DEFAULT_PERIOD_RE = re.compile(r"(year|month)((-|\+)[1-9]\d*)?")


_TOOLTIP_ATTR_RE = re.compile(r"^(t-att-|t-attf-)?data-tooltip(-template|-info)?$")


class ElementHandler:
    """What one arch element kind knows: how it validates itself, how it is
    prepared for the client, whether it makes its subtree editable and whether
    the view it roots runs onchanges. Registered per tag with ``register``; an
    addon that adds a view type registers a handler for its root tag."""

    __slots__ = ()
    tag: str = ""

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        return None

    def postprocess(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        return None

    def editable(self, view, node: _Element, name_manager: NameManager) -> bool | None:
        return None

    def can_onchange(self, view, node: _Element) -> bool | None:
        return None


class AttributeCheck:
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        return None


ELEMENT_HANDLERS: dict[str, ElementHandler] = {}
ATTRIBUTE_CHECKS: dict[str, AttributeCheck] = {}
_ATTRIBUTE_CHECK_PATTERNS: list[tuple[Any, AttributeCheck]] = []


def register(tag: str):
    def wrap(cls):
        cls.tag = tag
        ELEMENT_HANDLERS[tag] = cls()
        return cls

    return wrap


def register_attribute(*attrs: str, pattern=None):
    def wrap(cls):
        instance = cls()
        for attr in attrs:
            ATTRIBUTE_CHECKS[attr] = instance
        if pattern is not None:
            _ATTRIBUTE_CHECK_PATTERNS.append((pattern, instance))
        return cls

    return wrap


def attribute_check_for(attr: str) -> AttributeCheck | None:
    check = ATTRIBUTE_CHECKS.get(attr)
    if check is not None:
        return check
    for matcher, instance in _ATTRIBUTE_CHECK_PATTERNS:
        if matcher(attr):
            return instance
    return None


@register("calendar")
class CalendarHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        view._add_available_calendar_fields(node, name_manager, node_info)

    def postprocess(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        view._add_available_calendar_fields(node, name_manager, node_info)


@register("field")
class FieldHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        validate = node_info["validate"]

        name = node.get("name")
        if not name:
            raise view._prepare_view_error(
                _('Field tag must have a "name" attribute defined'), node
            )

        field = name_manager.model._fields.get(name)
        if field:
            view._narrow_model_groups(node_info, field)

            if validate and field.relational:
                domain = node.get("domain") or (
                    node_info["editable"] and field._description_domain(view.env)
                )
                if isinstance(domain, str):
                    desc = (
                        f'domain of <field name="{name}">'
                        if node.get("domain")
                        else f"domain of python field {name!r}"
                    )
                    view._check_domain_identifiers(
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
                raise view._prepare_view_error(msg, node)

            if field.type == "properties" and node_info["view_type"] != "search":
                name_manager.add_used_fields(
                    node,
                    {field._description_definition_record},
                    node_info,
                    use=("fieldname", field.name),
                )

            for child in list(node):
                if child.tag not in _NESTED_VIEW_TAGS:
                    continue
                node.remove(child)
                view._check_view(
                    child,
                    field.comodel_name,
                    view_type=child.tag,
                    editable=node_info["editable"],
                    node_info=node_info,
                )
                view._check_subview_schema(child, field.comodel_name)

        elif validate and name not in name_manager.field_info:
            msg = _(
                'Field "%(field_name)s" does not exist in model "%(model_name)s"',
                field_name=name,
                model_name=name_manager.model._name,
            )
            raise view._prepare_view_error(msg, node)

        name_manager.add_available_field(node, name, node_info, {"id": node.get("id")})

    def postprocess(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        name = node.get("name")
        if not name:
            return

        attrs = {"id": node.get("id")}
        field = name_manager.model._fields.get(name)

        if field:
            view._narrow_model_groups(node_info, field)
            if (
                node_info.get("view_type") == "form"
                and field.type in ("one2many", "many2many")
                and not node.get("widget")
                and node.get("invisible") not in ("1", "True")
                and not name_manager.parent
            ):
                for arch in view._get_x2many_missing_view_archs(field, node, node_info):
                    node.append(arch)

            if field.relational:
                domain = node.get("domain") or (
                    node_info["editable"] and field._description_domain(view.env)
                )
                if isinstance(domain, str):
                    vnames = get_expression_field_names(domain)
                    name_manager.add_used_fields(
                        node, vnames, node_info, ("domain", domain)
                    )
            if field.type == "properties":
                name_manager.add_used_fields(
                    node,
                    [field.definition_record],
                    node_info,
                    ("fieldname", field.name),
                )
            context = node.get("context")
            if context:
                vnames = get_expression_field_names(context)
                name_manager.add_used_fields(
                    node, vnames, node_info, ("context", context)
                )
            if field.type == "binary" and (field_filename := node.get("filename")):
                name_manager.add_used_fields(
                    node,
                    [field_filename],
                    node_info,
                    ("filename", field_filename),
                )

            for child in node:
                if child.tag in _NESTED_VIEW_TAGS:
                    node_info["children"] = []
                    view._postprocess_view(
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

        name_manager.add_available_field(node, name, node_info, attrs)

    def editable(self, view, node: _Element, name_manager: NameManager) -> bool:
        field = name_manager.model._fields.get(node.get("name"))
        return field is None or (
            field.is_editable() and node.get("readonly") not in ("1", "True")
        )


@register("groupby")
class GroupbyHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
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
                    raise view._prepare_view_error(msg, node)
                domain = node_info["editable"] and field._description_domain(view.env)
                if isinstance(domain, str):
                    desc = f"domain of python field '{name}'"
                    view._check_domain_identifiers(
                        node,
                        name_manager,
                        domain,
                        desc,
                        field.comodel_name,
                        node_info,
                    )

            groupby_node = E.groupby(*node)
            node_info["children"] = []
            try:
                view._check_view(
                    groupby_node,
                    field.comodel_name,
                    view_type="groupby",
                    editable=False,
                    node_info=node_info,
                )
            finally:
                node.extend(groupby_node)
            name_manager.add_available_field(node, name, node_info)

        elif node_info["validate"]:
            msg = _(
                "Field '%(field)s' found in 'groupby' node does not exist in model %(model)s",
                field=name,
                model=name_manager.model._name,
            )
            raise view._prepare_view_error(msg, node)

    def postprocess(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        name = node.get("name")
        if not name:
            return
        field = name_manager.model._fields.get(name)
        if not field or not field.comodel_name:
            return
        node_info["children"] = []
        scope = E.groupby(*node)
        view._postprocess_view(
            scope, field.comodel_name, editable=False, node_info=node_info
        )
        node.attrib.update(scope.attrib)
        node.extend(scope)
        name_manager.add_available_field(node, name, node_info)


@register("label")
class LabelHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        for_ = node.get("for")
        if not for_:
            msg = _(
                'Label tag must contain a "for". To match label style '
                "without corresponding field or button, use 'class=\"o_form_label\"'."
            )
            raise view._prepare_view_error(msg, node)
        name_manager.add_used_name(for_, '<label for="...">')

    def postprocess(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node.get("for"):
            return
        field = name_manager.model._fields.get(node.get("for"))
        if field:
            view._narrow_model_groups(node_info, field)


@register("search")
class SearchHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        searchpanels = [child for child in node if child.tag == "searchpanel"]
        if searchpanels:
            if len(searchpanels) > 1:
                raise view._prepare_view_error(
                    _("Search tag can only contain one search panel"), node
                )
            node_info["children"] = [
                child for child in node if child.tag != "searchpanel"
            ]
            view._check_view(
                searchpanels[0],
                name_manager.model._name,
                view_type="searchpanel",
                node_info=node_info,
                editable=False,
            )

    def postprocess(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        searchpanel = [child for child in node if child.tag == "searchpanel"]
        if searchpanel:
            view._postprocess_view(
                searchpanel[0],
                name_manager.model._name,
                editable=False,
                node_info=node_info,
            )
            node_info["children"] = [
                child for child in node if child.tag != "searchpanel"
            ]


@register("form")
class FormHandler(ElementHandler):
    __slots__ = ()

    def editable(self, view, node: _Element, name_manager: NameManager) -> bool:
        return True

    def can_onchange(self, view, node: _Element) -> bool:
        return True


@register("list")
class ListHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        editable_attr = node.get("editable")
        if editable_attr and editable_attr not in ["top", "bottom"]:
            msg = _(
                'The "editable" attribute of list views must be "top" or "bottom", received %(value)s',
                value=editable_attr,
            )
            raise view._prepare_view_error(msg, node)
        allowed_tags = (
            "field",
            "button",
            "control",
            "groupby",
            "widget",
            "header",
        )
        for child in node.iterchildren(tag=etree.Element):
            if child.tag not in allowed_tags:
                msg = _(
                    "List child can only have one of %(tags)s tag (not %(wrong_tag)s)",
                    tags=", ".join(allowed_tags),
                    wrong_tag=child.tag,
                )
                raise view._prepare_view_error(msg, child)

    def editable(self, view, node: _Element, name_manager: NameManager) -> bool:
        return bool(node.get("editable") or node.get("multi_edit"))

    def can_onchange(self, view, node: _Element) -> bool:
        return True


@register("kanban")
class KanbanHandler(ElementHandler):
    __slots__ = ()

    def can_onchange(self, view, node: _Element) -> bool:
        return True


@register("graph")
class GraphHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        for child in node.iterchildren(tag=etree.Element):
            if child.tag != "field":
                msg = _(
                    "A <graph> can only contains <field> nodes, found a <%s>",
                    child.tag,
                )
                raise view._prepare_view_error(msg, child)


@register("filter")
class FilterHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
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
            view._check_domain_identifiers(
                node,
                name_manager,
                domain,
                desc,
                name_manager.model._name,
                node_info,
            )
        if node.get("date") and (default_periods := node.get("default_period")):
            custom_options = {
                f"custom_{child_name}"
                for child in node.iterchildren(tag=etree.Element)
                if (child_name := child.get("name"))
            }
            for default_period in default_periods.split(","):
                if not _DEFAULT_PERIOD_RE.fullmatch(
                    default_period
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
                    raise view._prepare_view_error(msg, node)


@register("button")
class ButtonHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
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
                raise view._prepare_view_error(
                    _("Invalid special '%(value)s' in button", value=special),
                    node,
                )
        elif type_ == "object":
            if name:
                func = getattr(name_manager.model, name, None)
                if not callable(func):
                    msg = _(
                        "%(action_name)s is not a valid action on %(model_name)s",
                        action_name=name,
                        model_name=name_manager.model._name,
                    )
                    raise view._prepare_view_error(msg, node)
                if name.startswith("_") or getattr(func, "_api_private", False):
                    msg = _(
                        "%(method)s on %(model)s is private and cannot be called from a button",
                        method=name,
                        model=name_manager.model._name,
                    )
                    raise view._prepare_view_error(msg, node)
                try:
                    inspect.signature(
                        func, annotation_format=annotationlib.Format.FORWARDREF
                    ).bind()
                except TypeError:
                    msg = "%s on %s has parameters and cannot be called from a button"
                    view._log_view_warning(msg % (name, name_manager.model._name), node)
                name_manager.add_available_action(name)
        elif type_ == "action":
            if name:
                name_manager.add_required_action(name, node)
                name_manager.add_available_action(name)
        elif type_ and type_ not in view._get_client_button_types(
            node_info["view_type"]
        ):
            view._log_view_warning(f"Unknown button type {type_!r}", node)

        if node.get("icon"):
            description = f"A button with icon attribute ({node.get('icon')})"
            view._check_fa_class_accessibility(node, description)


@register("searchpanel")
class SearchpanelHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
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
                raise view._prepare_view_error(msg, child)


@register("page")
class PageHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return
        if node.getparent() is None or node.getparent().tag != "notebook":
            raise view._prepare_view_error(
                _("Page direct ancestor must be notebook"), node
            )


@register("img")
class ImgHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if node_info["validate"] and not any(node.get(alt) for alt in att_names("alt")):
            view._log_view_warning("<img> tag must contain an alt attribute", node)


@register("a")
class AHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if node_info["validate"] and any(
            "btn" in node.get(cl, "") for cl in att_names("class")
        ):
            if node.get("role") != "button":
                msg = '"<a>" tag with "btn" class must have "button" role'
                view._log_view_warning(msg, node)


@register("ul")
class UlHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if node_info["validate"]:
            view._check_dropdown_menu(node)


@register("div")
class DivHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        node_info: dict[str, Any],
    ) -> None:
        if node_info["validate"]:
            view._check_dropdown_menu(node)
            view._check_progress_bar(node)


@register_attribute("class", "t-att-class", "t-attf-class")
class ClassAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        view._check_classes(node, expr)


@register_attribute("context")
class ContextAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        try:
            vnames = get_expression_field_names(expr)
        except SyntaxError as e:
            message = _(
                "Invalid context: \u201c%(expr)s\u201d is not a valid Python expression \n\n %(error)s",
                expr=expr,
                error=e,
            )
            raise view._prepare_view_error(message, node) from e
        if vnames:
            name_manager.add_used_fields(node, vnames, node_info, ("context", expr))
        for key, val_ast in get_dict_asts(expr).items():
            if key != "group_by":
                continue
            if not isinstance(val_ast, ast.Constant) or not isinstance(
                val_ast.value, str
            ):
                msg = _(
                    '"group_by" value must be a string %(attribute)s=\u201c%(value)s\u201d',
                    attribute=attr,
                    value=expr,
                )
                raise view._prepare_view_error(msg, node)
            fname = val_ast.value.split(":")[0]
            if fname not in name_manager.model._fields:
                msg = _(
                    'Unknown field \u201c%(field)s\u201d in "group_by" value in %(attribute)s=\u201c%(value)s\u201d',
                    field=fname,
                    attribute=attr,
                    value=expr,
                )
                raise view._prepare_view_error(msg, node)


@register_attribute("col", "colspan")
class IntegerAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        if not expr.isdigit():
            raise view._prepare_view_error(
                _(
                    "\u201c%(attribute)s\u201d value must be an integer (%(value)s)",
                    attribute=attr,
                    value=expr,
                ),
                node,
            )


@register_attribute(pattern=lambda attr: attr.startswith("decoration-"))
class DecorationAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        vnames = get_expression_field_names(expr)
        if vnames:
            name_manager.add_used_fields(node, vnames, node_info, (attr, expr))


@register_attribute("data-bs-toggle")
class DataBsToggleAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        if expr != "tab":
            return
        if node.get("role") != "tab":
            view._log_view_warning(
                'tab link (data-bs-toggle="tab") must have "tab" role', node
            )
        aria_control = node.get("aria-controls") or node.get("t-att-aria-controls")
        if not aria_control and not node.get("t-attf-aria-controls"):
            view._log_view_warning(
                'tab link (data-bs-toggle="tab") must have "aria_control" defined',
                node,
            )
        if aria_control and "#" in aria_control:
            view._log_view_warning('aria-controls in tablink cannot contains "#"', node)


@register_attribute("role")
class RoleAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        if expr in ("presentation", "none"):
            view._log_view_warning(
                "A role cannot be `none` or `presentation`. "
                "All your elements must be accessible with screen readers, "
                "describe it.",
                node,
            )


@register_attribute("group")
class GroupAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        view._log_view_warning(
            "attribute 'group' is not valid.  Did you mean 'groups'?", node
        )


@register_attribute(pattern=_TOOLTIP_ATTR_RE.match)
class TooltipAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        raise view._prepare_view_error(
            _("Forbidden attribute used in arch (%s).", attr), node
        )


@register_attribute(pattern=lambda attr: attr.startswith("t-"))
class QwebAttributeCheck(AttributeCheck):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager: NameManager,
        attr: str,
        expr: str,
        node_info: dict[str, Any],
    ) -> None:
        view._check_qweb_directive(node, attr, node_info["view_type"])
        if COMP_REGEX.search(expr):
            raise view._prepare_view_error(
                _("Forbidden use of `__comp__` in arch."), node
            )
