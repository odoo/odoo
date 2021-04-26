# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models, _


class FleetVehicleModel(models.Model):
    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc'

    name = fields.Char('Model name', required=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True, help='Manufacturer of the vehicle')
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    image_128 = fields.Image(related='brand_id.image_128', readonly=True)
    active = fields.Boolean(default=True)
    vehicle_type = fields.Selection([('car', 'Car'), ('bike', 'Bike')], default='car', required=True)

    @api.depends('name', 'brand_id')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.brand_id.name:
                name = record.brand_id.name + '/' + name
            res.append((record.id, name))
        return res


class FleetVehicleModelBrand(models.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand of the vehicle'
    _order = 'model_count desc, name asc'

    name = fields.Char('Make', required=True)
    image_128 = fields.Image("Logo", max_width=128, max_height=128)
    model_count = fields.Integer(compute="_compute_model_count", string="", store=True)
    model_ids = fields.One2many('fleet.vehicle.model', 'brand_id')
    car_count = fields.Integer(compute="_compute_vehicle_count")
    bike_count = fields.Integer(compute="_compute_vehicle_count")

    @api.depends('model_ids')
    def _compute_model_count(self):
        Model = self.env['fleet.vehicle.model']
        for record in self:
            record.model_count = Model.search_count([('brand_id', '=', record.id)])

    @api.depends('model_ids')
    def _compute_vehicle_count(self):
        car_dict = defaultdict(int)
        bike_dict = defaultdict(int)

        vehicle = self.env['fleet.vehicle.model'].read_group(
            [('brand_id', 'in', self.ids)],
            ['brand_id', 'vehicle_type'],
            ['brand_id', 'vehicle_type'],
            lazy=False
        )
        for data in vehicle:
            if data['vehicle_type'] == 'car':
                car_dict[data['brand_id'][0]] = data['__count']
            elif data['vehicle_type'] == 'bike':
                bike_dict[data['brand_id'][0]] = data['__count']
        for brand in self:
            brand.car_count = car_dict[brand.id]
            brand.bike_count = bike_dict[brand.id]

    def action_brand_model(self):
        self.ensure_one()
        vehicle_type = self.env.context.get('vehicle_type', False)
        view = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'fleet.vehicle.model',
            'name': _('Models'),
            'context': {'search_default_brand_id': self.id, 'default_brand_id': self.id}
        }
        if vehicle_type:
            view['domain'] = [('brand_id', '=', self.id), ('vehicle_type', '=', vehicle_type)]

        return view
