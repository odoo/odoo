from collections.abc import Iterable

from odoo import models, fields
from odoo.fields import Domain
from odoo.tools import SQL


class PropertiesBaseDefinitionMixin(models.AbstractModel):
    """Mixin that add properties without parent on a model."""

    _name = "properties.base.definition.mixin"
    _description = "Properties Base Definition Mixin"

    def _get_properties_base_definition_id(self):
        return self.env["properties.base.definition"].sudo() \
            ._get_definition_id_for_property_field(self._name, "properties")

    properties = fields.Properties(
        string="Properties",
        definition="properties_base_definition_id.properties_definition",
        copy=True,
    )
    properties_base_definition_id = fields.Many2one(
        "properties.base.definition",
        compute="_compute_properties_base_definition_id",
        compute_sql="_compute_sql_properties_base_definition_id",
        compute_sudo=True,
        # needed to add the default properties values
        default=_get_properties_base_definition_id,
    )

    def _compute_properties_base_definition_id(self):
        self.properties_base_definition_id = self._get_properties_base_definition_id()

    def _compute_sql_properties_base_definition_id(self, table):
        # Allow the export to work
        parent = self._get_properties_base_definition_id()
        return SQL("%s", parent)

    def _search_properties_base_definition_id(self, operator, value):
        if operator != "in":
            return NotImplemented

        properties_base_definition_id = self._get_properties_base_definition_id()

        if not isinstance(value, Iterable):
            value = (value,)
        return Domain.TRUE if properties_base_definition_id in value else Domain.FALSE
