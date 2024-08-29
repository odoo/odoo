# -*- coding: utf-8 -*-
from odoo.addons import fleet
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FleetVehicleOdometer(models.Model, fleet.FleetVehicleOdometer):

    driver_employee_id = fields.Many2one(
        related='vehicle_id.driver_employee_id', string='Driver (Employee)',
        readonly=True,
    )
