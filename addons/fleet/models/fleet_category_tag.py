# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class FleetCategoryTag(models.Model):
    _name = 'fleet.category.tag'
    _description = 'Vehicle Fleet Category'

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'Name must be unique.'),
    ]

    name = fields.Char()
    color = fields.Integer()
