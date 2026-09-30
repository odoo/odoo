# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EstatePropertyTag(models.Model):
    _name = 'estate.property.tag'
    _description = 'Property Tag'

    name = fields.Char(required=True)

    _unique_name = models.Constraint('UNIQUE(name)', 'Property tag names must be unique.')
