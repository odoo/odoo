from odoo import _, api, models
from odoo.exceptions import AccessError


class PropertiesBaseDefinition(models.Model):
    _inherit = "properties.base.definition"

    @api.model
    def get_properties_base_definition(self, model_name, field_name):
        """Return the base properties definition if we can read the model."""
        model = self.env[model_name]
        model.check_access("read")
        if model._fields[field_name].type != "properties":
            raise AccessError(_("You can not read that field definition."))
        return self.sudo().web_search_read(
            [
                ["properties_field_id.name", "=", field_name],
                ["properties_field_id.model", "=", model_name],
            ],
            specification={"display_name": {}, "properties_definition": {}},
        )
