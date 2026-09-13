from __future__ import annotations

import typing

from lxml import etree

from odoo import _, fields, models

from odoo.addons.base.models.ir_ui_view_arch import ElementHandler, register

if typing.TYPE_CHECKING:
    from typing import Any

    from lxml.etree import _Element

HIERARCHY_VALID_ATTRIBUTES = {
    "__validate__",
    "class",
    "js_class",
    "string",
    "create",
    "edit",
    "delete",
    "parent_field",
    "child_field",
    "icon",
    "draggable",
    "default_order",
    "sample",
}

CARD_TEMPLATE_NAME = "hierarchy-box"


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(selection_add=[("hierarchy", "Hierarchy")])

    def _is_qweb_based_view(self, view_type):
        return super()._is_qweb_based_view(view_type) or view_type == "hierarchy"

    def _check_hierarchy_relation_fields(self, node: _Element, model) -> None:
        for attribute, expected_type in (
            ("parent_field", "many2one"),
            ("child_field", "one2many"),
        ):
            field_name = node.get(attribute)
            if not field_name:
                continue
            field = model._fields.get(field_name)
            if field is None:
                msg = _(
                    "Invalid %(attribute)s: %(field_name)s does not exist on %(model)s",
                    attribute=attribute,
                    field_name=field_name,
                    model=model._name,
                )
                raise self._prepare_view_error(msg, node)
            if field.type != expected_type:
                msg = _(
                    "Invalid %(attribute)s: %(field_name)s is a %(actual_type)s, expected a %(expected_type)s",
                    attribute=attribute,
                    field_name=field_name,
                    actual_type=field.type,
                    expected_type=expected_type,
                )
                raise self._prepare_view_error(msg, node)
            if field.comodel_name != model._name:
                msg = _(
                    "Invalid %(attribute)s: %(field_name)s points at %(comodel)s, expected %(model)s",
                    attribute=attribute,
                    field_name=field_name,
                    comodel=field.comodel_name,
                    model=model._name,
                )
                raise self._prepare_view_error(msg, node)

    def _get_view_info(self):
        return {
            "hierarchy": {"icon": "fa-solid fa-share-alt fa-rotate-90"}
        } | super()._get_view_info()


@register("hierarchy")
class HierarchyHandler(ElementHandler):
    __slots__ = ()

    def check(
        self,
        view,
        node: _Element,
        name_manager,
        node_info: dict[str, Any],
    ) -> None:
        if not node_info["validate"]:
            return

        seen_templates = False
        for child in node.iterchildren(tag=etree.Element):
            if child.tag == "templates":
                if seen_templates:
                    msg = _("Hierarchy view can contain only one templates tag")
                    raise view._prepare_view_error(msg, child)
                seen_templates = True
            elif child.tag != "field":
                msg = _(
                    "Hierarchy child can only be field or template, got %s", child.tag
                )
                raise view._prepare_view_error(msg, child)

        remaining = set(node.attrib) - HIERARCHY_VALID_ATTRIBUTES
        if remaining:
            msg = _(
                "Invalid attributes (%(invalid_attributes)s) in hierarchy view. Attributes must be in (%(valid_attributes)s)",
                invalid_attributes=remaining,
                valid_attributes=HIERARCHY_VALID_ATTRIBUTES,
            )
            raise view._prepare_view_error(msg, node)

        if not node.xpath(f".//*[@t-name='{CARD_TEMPLATE_NAME}']"):
            msg = _(
                "Hierarchy view must define a 'hierarchy-box' template to render its cards"
            )
            raise view._prepare_view_error(msg, node)

        if name_manager is not None:
            view._check_hierarchy_relation_fields(node, name_manager.model)
