# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class FleetVehicleModel(models.Model):
    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc'

    name = fields.Char('Model name', required=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True, help='Manufacturer of the vehicle')
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    manager_id = fields.Many2one('res.users', 'Fleet Manager', default=lambda self: self.env.uid,
                                 domain=lambda self: [('groups_id', 'in', self.env.ref('fleet.fleet_group_manager').id)])
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

    def write(self, vals):
        if 'manager_id' in vals:
            old_manager = self.manager_id.id if self.manager_id else None

            self.env['fleet.vehicle'].search([('model_id', '=', self.id), ('manager_id', '=', old_manager)]).write({'manager_id': vals['manager_id']})

        return super(FleetVehicleModel, self).write(vals)


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
