from odoo import fields, models

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Estate property tags"
    _order = "name"

    name = fields.Char(required=True)
    color = fields.Integer()
    _sql_constraints = [
        ('unique_tag', 'unique(name)', 'A property tag name must be unique')
    ]