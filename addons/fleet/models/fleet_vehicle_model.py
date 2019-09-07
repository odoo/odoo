# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FleetVehicleModel(models.Model):
    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc'

    name = fields.Char('Model name', required=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True, help='Manufacturer of the vehicle')
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    manager_id = fields.Many2one('res.users', 'Fleet Manager', default=lambda self: self.env.uid,
                                 domain=lambda self: [('groups_id', 'in', self.env.ref('fleet.fleet_group_manager').id)])
    image_128 = fields.Image(related='brand_id.image_128', readonly=False)

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
    _order = 'name asc'

    name = fields.Char('Make', required=True)
    image_128 = fields.Image("Logo", max_width=128, max_height=128)
