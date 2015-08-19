# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class FleetVehicleCost(models.Model):
    _name = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle'
    _order = 'date desc, vehicle_id asc, id desc'

    name = fields.Char(related='vehicle_id.name', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True,
                                 help='Vehicle concerned by this log')
    cost_subtype_id = fields.Many2one('fleet.service.type', string='Type',
                                      help='Cost type purchased with this cost')
    amount = fields.Float(string='Total Price')
    cost_type = fields.Selection(selection=[('contract', 'Contract'), ('services', 'Services'),
                                            ('fuel', 'Fuel'), ('other', 'Other')],
                                 string='Category of the cost', help='For internal purpose only',
                                 required=True, default='other')
    parent_id = fields.Many2one('fleet.vehicle.cost', string='Parent', help='Parent cost to this current cost')
    cost_ids = fields.One2many('fleet.vehicle.cost', 'parent_id', string='Included Services')
    odometer_id = fields.Many2one('fleet.vehicle.odometer', string='Odometer',
                                  help='Odometer measure of the vehicle at the moment of this log')
    odometer = fields.Float(compute='_compute_get_odometer', inverse='_compute_set_odometer', string='Odometer Value',
                            help='Odometer measure of the vehicle at the moment of this log', store=True)
    odometer_unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    date = fields.Date(help='Date when the cost has been executed')
    contract_id = fields.Many2one('fleet.vehicle.log.contract', string='Contract',
                                  help='Contract attached to this cost')
    auto_generated = fields.Boolean('Automatically Generated', readonly=True, required=True)

    @api.one
    @api.depends('odometer_id')
    def _compute_get_odometer(self):
        self.odometer = self.odometer_id and self.odometer_id.value

    @api.one
    def _compute_set_odometer(self):
        if not self.odometer:
            raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
        odometer = self.env['fleet.vehicle.odometer'].create({
            'value': self.odometer,
            'date': self.date or fields.Date.context_today(self),
            'vehicle_id': self.vehicle_id.id})
        self.odometer_id = odometer.id

    @api.model
    def create(self, values):
        # make sure that the data are consistent with values of parent and contract records given
        if values.get('parent_id'):
            parent = self.browse(values['parent_id'])
            values['vehicle_id'] = parent.vehicle_id.id
            values['date'] = parent.date
            values['cost_type'] = parent.cost_type
        if values.get('contract_id'):
            contract = self.env['fleet.vehicle.log.contract'].browse(values['contract_id'])
            values['vehicle_id'] = contract.vehicle_id.id
            values['cost_subtype_id'] = contract.cost_subtype_id.id
            values['cost_type'] = contract.cost_type
        if 'odometer' in values and not values['odometer']:
            # if received value for odometer is 0, then remove it from the data as it would result to the creation of a
            # odometer log with 0, which is to be avoided
            del(values['odometer'])
        return super(FleetVehicleCost, self).create(values)
