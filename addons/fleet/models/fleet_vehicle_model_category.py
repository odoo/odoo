# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FleetVehicleModelCategory(models.Model):
    _name = 'fleet.vehicle.model.category'
    _description = 'Category of the model'
    _order = 'sequence asc, id asc'

    _name_uniq = models.Constraint(
        'UNIQUE (name)',
        'Category name must be unique',
    )

    name = fields.Char(required=True)
    sequence = fields.Integer()
