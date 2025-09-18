from typing import Any

from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError


class PropertiesBaseDefinition(models.Model):
    _inherit = "properties.base.definition"

    @api.model
    def get_properties_base_definition(
        self, model_name: str, field_name: str
    ) -> dict[str, Any]:
        """Return the base properties definition if we can read the model."""
        model = self.env.get(model_name)
        if model is None:
            raise ValidationError(_("Invalid model: %s", model_name))
        model.check_access("read")
        field = model._fields.get(field_name)
        if field is None or field.type != "properties":
            raise AccessError(_("You can not read that field definition."))
        return self.sudo().web_search_read(
            [
                ["properties_field_id.name", "=", field_name],
                ["properties_field_id.model", "=", model_name],
            ],
            specification={"display_name": {}, "properties_definition": {}},
        )
