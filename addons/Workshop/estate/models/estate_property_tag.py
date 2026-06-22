from odoo import models,fields

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Estate Property Tags"

    name = fields.Char(required=True)
    color = fields.Integer("Color")

    _unique_tag_name = models.Constraint(
        'UNIQUE(name)',
        'A property tag must be unique'
    )