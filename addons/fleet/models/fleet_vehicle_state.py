# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FleetVehicleState(models.Model):
    _name = 'fleet.vehicle.state'
    _order = 'sequence asc'
    _description = 'Vehicle Status'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer()
    fold = fields.Boolean(string='Folded in Kanban')

    _fleet_state_name_unique = models.Constraint(
        'unique(name)',
        'State name already exists',
    )
