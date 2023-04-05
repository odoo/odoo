from odoo import fields, models
class estate_property_tag(models.Model):
    _name = "estate.property.tag"
    _description = "Test Model tag"
    _order = "name"
    Color = fields.Integer(1)
    name = fields.Char(required=True)

    _sql_constraints = [('unique_code', 'unique(name)', 'name must be unique ')]


