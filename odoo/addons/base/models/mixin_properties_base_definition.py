from collections.abc import Iterable
from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class MixinPropertiesBaseDefinition(models.AbstractModel):
    _name = "mixin.properties.base.definition"
    _description = "Properties Base Definition Mixin"

    properties = fields.Properties(
        definition="properties_base_definition_id.properties_definition",
        copy=True,
    )
    properties_base_definition_id = fields.Many2one(
        comodel_name="properties.base.definition",
        compute="_compute_properties_base_definition_id",
        search="_search_properties_base_definition_id",
        value_sql="_properties_base_definition_id_sql",
    )

    def _compute_properties_base_definition_id(self) -> None:
        definition = (
            self.env["properties.base.definition"]
            .sudo()
            ._get_definition_for_property_field(self._name, "properties")
        )
        _debug.logic(
            "definition_computed",
            model=self._name,
            definition=definition.id,
            records=len(self),
        )
        self.properties_base_definition_id = definition

    def _properties_base_definition_id_sql(
        self, field: fields.Field, alias: str, query: Any = None
    ) -> SQL:
        parent = (
            self.env["properties.base.definition"]
            .sudo()
            ._get_definition_id_for_property_field(self._name, "properties")
        )
        _debug.logic("definition_to_sql", model=self._name, definition=parent)
        return SQL("%s::int4", parent)

    def _search_properties_base_definition_id(
        self, operator: str, value: Any
    ) -> Domain:
        if operator not in ("in", "not in"):
            _debug.logic(
                "definition_search_unsupported", model=self._name, operator=operator
            )
            raise NotImplementedError(
                f"Unsupported operator {operator!r} for properties_base_definition_id"
            )

        properties_base_definition_id = (
            self.env["properties.base.definition"]
            .sudo()
            ._get_definition_id_for_property_field(self._name, "properties")
        ) or False

        if not isinstance(value, Iterable):
            value = (value,)
        matched = (properties_base_definition_id in value) == (operator == "in")
        _debug.logic(
            "definition_searched",
            model=self._name,
            definition=properties_base_definition_id,
            operator=operator,
            matched=matched,
        )
        return Domain.TRUE if matched else Domain.FALSE

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        parent = (
            self.env["properties.base.definition"]
            .sudo()
            ._get_or_create_definition_id_for_property_field(self._name, "properties")
        )
        _debug.lifecycle(
            "definition_attached",
            model=self._name,
            definition=parent,
            count=len(vals_list),
        )
        return super().create(
            [{**vals, "properties_base_definition_id": parent} for vals in vals_list]
        )
