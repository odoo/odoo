from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import ormcache


class PropertiesBaseDefinition(models.Model):
    """Models storing the properties definition of the record without parent."""

    _name = "properties.base.definition"
    _description = "Properties Base Definition"
    _log_access = False

    properties_field_id = fields.Many2one(
        "ir.model.fields",
        required=True,
        ondelete="cascade",
    )
    properties_definition = fields.PropertiesDefinition("Properties Definition")

    _unique_properties_field_id = models.Constraint(
        "UNIQUE(properties_field_id)",
        "Only one definition per properties field",
    )

    @api.depends("properties_field_id")
    def _compute_display_name(self):
        for definition in self:
            if not definition.properties_field_id.model:
                definition.display_name = False
                continue

            definition.display_name = _(
                "%s Properties",
                self.env[definition.properties_field_id.model]._description,
            )

    @api.constrains("properties_field_id")
    def _check_properties_field_id(self):
        if set(self.mapped("properties_field_id.ttype")) - {"properties"}:
            raise ValidationError(
                _("The definition needs to be linked to a properties field.")
            )

    def _get_record_for_properties(self, model_name, field_name):
        return self.browse(self._get_record_id_for_properties(model_name, field_name))

    @ormcache("model_name", "field_name")
    def _get_record_id_for_properties(self, model_name, field_name):
        definition_record = self.sudo().search(
            [
                ("properties_field_id.model", "=", model_name),
                ("properties_field_id.name", "=", field_name),
            ],
            limit=1,
        )
        if not definition_record:
            field = self.env["ir.model.fields"].sudo()._get(model_name, field_name)
            definition_record = self.sudo().create(
                {
                    "properties_field_id": field.id,
                },
            )
        return definition_record.id
