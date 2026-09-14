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
    )

    def _compute_properties_base_definition_id(self) -> None:
        self.properties_base_definition_id = (
            self.env["properties.base.definition"]
            .sudo()
            ._get_definition_for_property_field(self._name, "properties")
        )

    def _search_properties_base_definition_id(
        self, operator: str, value: Any
    ) -> Domain:
        if operator not in ("in", "not in"):
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
        for vals in vals_list:
            vals["properties_base_definition_id"] = parent
        _debug.lifecycle(
            "definition_attached",
            model=self._name,
            definition=parent,
            count=len(vals_list),
        )
        return super().create(vals_list)

    def _field_to_sql(self, alias: str, fname: str, query: Any = None) -> SQL:
        if fname == "properties_base_definition_id":
            parent = (
                self.env["properties.base.definition"]
                .sudo()
                ._get_definition_id_for_property_field(self._name, "properties")
            )
            return SQL("%s::int4", parent)

        return super()._field_to_sql(alias, fname, query)
