# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstatePropertyTag(models.Model):
    """A free label characterizing properties, such as "cozy" or "renovated"."""

    _name = "estate.property.tag"
    _description = "Real Estate Property Tag"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    # Index in the palette of the web client, used by the many2many_tags widget
    color = fields.Integer(string="Color")

    _unique_name = models.Constraint("UNIQUE(name)", "A tag with this name already exists.")
