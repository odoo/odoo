from odoo import models,fields,api

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Estate Property Types"

    name = fields.Char(required=True)
    property_ids = fields.One2many("estate.property","property_type_id")

    _unique_type_name = models.Constraint(
        'UNIQUE(name)',
        'A property type must be unique'
    )
