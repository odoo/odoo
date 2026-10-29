# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstatePropertyType(models.Model):
    """The kind of property (house, apartment, ...), configured by the agency."""

    _name = "estate.property.type"
    _description = "Real Estate Property Type"

    name = fields.Char(string="Name", required=True)

    _unique_name = models.Constraint(
        "UNIQUE(name)", "A property type with this name already exists."
    )
