# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class FleetVehicleLogContract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    purchaser_employee_id = fields.Many2one(
        related='vehicle_id.driver_employee_id',
        string='Current Driver (Employee)',
    )
    fleet_is_internal = fields.Boolean(related='vehicle_id.fleet_is_internal')

class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    purchaser_employee_id = fields.Many2one(
        'hr.employee', string="Driver (Employee)",
        compute='_compute_purchaser_employee_id', readonly=False, store=True,
    )
    fleet_is_internal = fields.Boolean(related='vehicle_id.fleet_is_internal')

    @api.depends('vehicle_id', 'purchaser_employee_id')
    def _compute_purchaser_id(self):
        internal = self.filtered(lambda r: r.fleet_is_internal)
        super(FleetVehicleLogServices, (self - internal))._compute_purchaser_id()
        for service in internal:
            service.purchaser_id = service.purchaser_employee_id.address_home_id

    @api.depends('vehicle_id')
    def _compute_purchaser_employee_id(self):
        for service in self:
            service.purchaser_employee_id = service.vehicle_id.driver_employee_id
