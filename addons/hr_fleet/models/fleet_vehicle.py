# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    mobility_card = fields.Char(compute='_compute_mobility_card', store=True)

    @api.depends('driver_id')
    def _compute_mobility_card(self):
        for vehicle in self:
            vehicle.mobility_card = vehicle.driver_id.user_ids[:1].employee_id.mobility_card
