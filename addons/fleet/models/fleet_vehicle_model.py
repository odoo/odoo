# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class FleetVehicleModel(models.Model):
    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc'

    name = fields.Char('Model name', required=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True, help='Manufacturer of the vehicle')
    category_id = fields.Many2one('fleet.vehicle.model.category', 'Category')
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    image_128 = fields.Image(related='brand_id.image_128', readonly=True)
    active = fields.Boolean(default=True)
    vehicle_type = fields.Selection([('car', 'Car'), ('bike', 'Bike')], default='car', required=True)
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], 'Transmission', help='Transmission Used by the vehicle')
    vehicle_count = fields.Integer(compute='_compute_vehicle_count')

    @api.depends('name', 'brand_id')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.brand_id.name:
                name = record.brand_id.name + '/' + name
            res.append((record.id, name))
        return res

    def _compute_vehicle_count(self):
        group = self.env['fleet.vehicle'].read_group(
            [('model_id', 'in', self.ids)], ['id', 'model_id'], groupby='model_id', lazy=False,
        )
        count_by_model = {entry['model_id'][0]: entry['__count'] for entry in group}
        for model in self:
            model.vehicle_count = count_by_model.get(model.id, 0)

    def action_model_vehicle(self):
        self.ensure_one()
        view = {
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'res_model': 'fleet.vehicle',
            'name': _('Vehicles'),
            'context': {'search_default_model_id': self.id, 'default_model_id': self.id}
        }

        return view

class FleetVehicleModelBrand(models.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand of the vehicle'
    _order = 'model_count desc, name asc'

    name = fields.Char('Make', required=True)
    image_128 = fields.Image("Logo", max_width=128, max_height=128)
    model_count = fields.Integer(compute="_compute_model_count", string="", store=True)
    model_ids = fields.One2many('fleet.vehicle.model', 'brand_id')

    @api.depends('model_ids')
    def _compute_model_count(self):
        Model = self.env['fleet.vehicle.model']
        for record in self:
            record.model_count = Model.search_count([('brand_id', '=', record.id)])

    def action_brand_model(self):
        self.ensure_one()
        view = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'fleet.vehicle.model',
            'name': 'Models',
            'context': {'search_default_brand_id': self.id, 'default_brand_id': self.id}
        }

        return view

class FleetVehicleModelCategory(models.Model):
    _name = 'fleet.vehicle.model.category'
    _description = 'Category of the model'
    _order = 'sequence asc, id asc'

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', 'Category name must be unique')
    ]

    name = fields.Char(required=True)
    sequence = fields.Integer()
