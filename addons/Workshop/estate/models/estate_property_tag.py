from odoo import api, models, fields

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "property tags"

    # name = fields.Char()
    name = fields.Char(required=True)
    color = fields.Integer("color")

    _unique_tag_name = models.Constraint("UNIQUE(name)", "A property tag must be unique")

    _check_name_not_empty = models.Constraint("CHECK(name != '')", "A property tag name cannot be empty")