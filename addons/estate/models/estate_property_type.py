from odoo import fields, models
class estate_property_type(models.Model):
    _name = "estate.property.type"
    _description = "Test Model type"
    _order = "name"


    name = fields.Char(required=True)

    sequence = fields.Integer("Sequence", default=10)

    _sql_constraints = [('unique_code2', 'unique(name)', 'name must be unique ')]

    property_ids = fields.One2many("estate.property", "property_type_id", string="Properties")




