from collections.abc import Iterable

from odoo import models, api, fields
from odoo.fields import Domain
from odoo.tools import SQL


class PropertiesBaseDefinitionMixin(models.AbstractModel):
    """Mixin that add properties without parent on a model."""

    _name = "properties.base.definition.mixin"
    _description = "Properties Base Definition Mixin"

    properties = fields.Properties(
        string="Properties",
        definition="properties_base_definition_id.properties_definition",
        copy=True,
    )
    properties_base_definition_id = fields.Many2one(
        "properties.base.definition",
        compute="_compute_properties_base_definition_id",
        search="_search_properties_base_definition_id",
    )

    def _compute_properties_base_definition_id(self):
        self.properties_base_definition_id = self.env["properties.base.definition"] \
            .sudo()._get_definition_for_property_field(self._name, "properties")

    def _search_properties_base_definition_id(self, operator, value):
        if operator != "in":
            return NotImplemented

        properties_base_definition_id = self.env["properties.base.definition"] \
            .sudo()._get_definition_id_for_property_field(self._name, "properties")

        if not isinstance(value, Iterable):
            value = (value,)
        return Domain.TRUE if properties_base_definition_id in value else Domain.FALSE

    @api.model_create_multi
    def create(self, vals_list):
        parent = self.env["properties.base.definition"] \
            ._get_definition_id_for_property_field(self._name, "properties")
        for vals in vals_list:
            # Needed to add the default properties values
            vals["properties_base_definition_id"] = parent
        return super().create(vals_list)

    def _field_to_sql(self, alias, fname, query=None):
        if fname == 'properties_base_definition_id':
            # Allow the export to work
            parent = self.env["properties.base.definition"] \
                ._get_definition_id_for_property_field(self._name, "properties")
            return SQL("%s", parent)

        return super()._field_to_sql(alias, fname, query)
