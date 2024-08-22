# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetVehicleOdometer(models.Model):
    _name = 'fleet.vehicle.odometer'
    _description = 'Odometer log for a vehicle'
    _order = 'date desc'

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float('Odometer Value', group_operator="max")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver", readonly=False)

    @api.depends('vehicle_id', 'date')
    def _compute_vehicle_log_name(self):
        for record in self:
            name = record.vehicle_id.name
            if not name:
                name = str(record.date)
            elif record.date:
                name += ' / ' + str(record.date)
            record.name = name

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.unit = self.vehicle_id.odometer_unit

    def _check_odometer(self):
        vehicle_ids = list(set(self.vehicle_id.ids))
        odometers_to_check = self.search([('vehicle_id', 'in', vehicle_ids)], order='date')

        grouped_odometers = {}
        for odometer in odometers_to_check:
            if not grouped_odometers.get(odometer.vehicle_id.id):
                grouped_odometers[odometer.vehicle_id.id] = odometer
            else:
                grouped_odometers[odometer.vehicle_id.id] |= odometer

        for odometer in self:
            this_vehicle_odometers = grouped_odometers.get(odometer.vehicle_id.id, self.env['fleet.vehicle.odometer'])
            for odometer_to_check in this_vehicle_odometers:
                if odometer.date < odometer_to_check.date:
                    if odometer.value > odometer_to_check.value:
                        raise UserError(_('You cannot set an odometer value higher than one from the future.'))
                elif odometer.date == odometer_to_check.date:
                    if odometer.id > odometer_to_check.id:
                        if odometer.value < odometer_to_check.value:
                            raise UserError(_('You cannot set an odometer value lower than one from a previous record.'))
                    elif odometer.id < odometer_to_check.id:
                        if odometer.value > odometer_to_check.value:
                            raise UserError(_('You cannot set an odometer value higher than one from a future record.'))
                else:
                    if odometer.value < odometer_to_check.value:
                        raise UserError(_('You cannot set an odometer value lower than one from the past.'))

    @api.model
    def create(self, vals):
        new_odometers = super().create(vals)
        new_odometers._check_odometer()
        return new_odometers

    def write(self, vals):
        res = super().write(vals)
        self._check_odometer()
        return res
