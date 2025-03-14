from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import ormcache


class PropertiesBaseDefinition(models.Model):
    """Models storing the properties definition of the record without parent."""

    _name = "properties.base.definition"
    _description = "Properties Base Definition"
    _log_access = False

    display_name = fields.Char("Display Name", compute="_compute_display_name")
    properties_field_id = fields.Many2one("ir.model.fields")
    properties_definition = fields.PropertiesDefinition("Properties Definition")

    @api.depends("properties_field_id")
    def _compute_display_name(self):
        for definition in self:
            if not definition.properties_field_id.model:
                definition.display_name = False
                continue

            definition.display_name = _("%s Properties", self.env[definition.properties_field_id.model]._description)

    @api.constrains("properties_field_id")
    def _check_properties_field_id(self):
        if set(self.mapped("properties_field_id.ttype")) - {"properties"}:
            raise ValidationError(
                _("The definition needs to be linked to a properties field.")
            )

    @ormcache('model_name', 'field_name')
    def _get_or_create_record(self, model_name, field_name):
        definition_record = self.sudo().search(
            [
                ("properties_field_id.model", "=", model_name),
                ("properties_field_id.name", "=", field_name),
            ],
            limit=1,
        )
        if not definition_record:
            definition_record = self.sudo().create(
                {
                    "properties_field_id": self.env["ir.model.fields"]
                    .sudo()
                    ._get(model_name, field_name)
                    .id,
                },
            )
        return definition_record
