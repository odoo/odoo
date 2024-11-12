# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    purchaser_employee_id = fields.Many2one(
        'hr.employee', string="Driver (Employee)",
        compute='_compute_purchaser_employee_id', readonly=False, store=True,
    )

    @api.depends('vehicle_id', 'purchaser_employee_id')
    def _compute_purchaser_id(self):
        internals = self.filtered(lambda r: r.purchaser_employee_id)
        super(FleetVehicleLogServices, (self - internals))._compute_purchaser_id()
        for service in internals:
            service.purchaser_id = service.purchaser_employee_id.work_contact_id

    @api.depends('vehicle_id')
    def _compute_purchaser_employee_id(self):
        for service in self:
            service.purchaser_employee_id = service.vehicle_id.driver_employee_id
