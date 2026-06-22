from odoo import api, models, fields

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "property types"

    name = fields.Char(required=True) 

    _unique_type_name = models.Constraint("UNIQUE(name)", "A property type must be unique")
    _check_name_not_empty = models.Constraint("CHECK(name != '')", "A property type name cannot be empty")

    property_ids = fields.One2many("estate.property", "property_type_id")