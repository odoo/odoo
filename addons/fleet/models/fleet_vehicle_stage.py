# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp import fields, models, _


class FleetVehicleStage(models.Model):
    _name = 'fleet.vehicle.stage'
    _order = 'sequence, id '

    name = fields.Char(required=True)
    sequence = fields.Integer(help="Used to order the vehicle stages")

    _sql_constraints = [('fleet_stage_name_unique', 'unique(name)', _('Stage name already exists'))]
