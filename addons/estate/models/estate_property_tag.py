# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstatePropertyTag(models.Model):
    _name = 'estate.property.tag'
    _description = 'Property Tag'
    _order = 'name'

    name = fields.Char(required=True)
    color = fields.Integer()

    _unique_name = models.Constraint('UNIQUE(name)', 'Property tag names must be unique.')
