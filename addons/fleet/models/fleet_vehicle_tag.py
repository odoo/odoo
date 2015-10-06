# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class FleetVehicleTag(models.Model):
    _name = 'fleet.vehicle.tag'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer('Color Index')
