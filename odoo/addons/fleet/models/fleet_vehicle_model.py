# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.osv import expression


FUEL_TYPES = [
    ('diesel', 'Diesel'),
    ('gasoline', 'Gasoline'),
    ('full_hybrid', 'Full Hybrid'),
    ('plug_in_hybrid_diesel', 'Plug-in Hybrid Diesel'),
    ('plug_in_hybrid_gasoline', 'Plug-in Hybrid Gasoline'),
    ('cng', 'CNG'),
    ('lpg', 'LPG'),
    ('hydrogen', 'Hydrogen'),
    ('electric', 'Electric'),
]

class FleetVehicleModel(models.Model):
    _name = 'fleet.vehicle.model'
    _inherit = ['avatar.mixin']
    _description = 'Model of a vehicle'
    _order = 'name asc'

    name = fields.Char('Model name', required=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True)
    category_id = fields.Many2one('fleet.vehicle.model.category', 'Category')
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    image_128 = fields.Image(related='brand_id.image_128', readonly=True)
    active = fields.Boolean(default=True)
    vehicle_type = fields.Selection([('car', 'Car'), ('bike', 'Bike')], default='car', required=True)
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], 'Transmission')
    vehicle_count = fields.Integer(compute='_compute_vehicle_count', search='_search_vehicle_count')
    model_year = fields.Integer()
    color = fields.Char()
    seats = fields.Integer(string='Seats Number')
    doors = fields.Integer(string='Doors Number')
    trailer_hook = fields.Boolean(default=False, string='Trailer Hitch')
    default_co2 = fields.Float('CO2 Emissions')
    co2_standard = fields.Char()
    default_fuel_type = fields.Selection(FUEL_TYPES, 'Fuel Type', default='electric')
    power = fields.Integer('Power')
    horsepower = fields.Integer()
    horsepower_tax = fields.Float('Horsepower Taxation')
    electric_assistance = fields.Boolean(default=False)
    vehicle_properties_definition = fields.PropertiesDefinition('Vehicle Properties')

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if operator != 'ilike' or (name or '').strip():
            name_domain = ['|', ('name', 'ilike', name), ('brand_id.name', 'ilike', name)]
            domain = expression.AND([name_domain, domain])
        return self._search(domain, limit=limit, order=order)

    @api.depends('brand_id')
    def _compute_display_name(self):
        for record in self:
            name = record.name
            if record.brand_id.name:
                name = f"{record.brand_id.name}/{name}"
            record.display_name = name

    def _compute_vehicle_count(self):
        group = self.env['fleet.vehicle']._read_group(
            [('model_id', 'in', self.ids)], ['model_id'], aggregates=['__count'],
        )
        count_by_model = {model.id: count for model, count in group}
        for model in self:
            model.vehicle_count = count_by_model.get(model.id, 0)

    @api.model
    def _search_vehicle_count(self, operator, value):
        if operator not in ['=', '!=', '<', '>'] or not isinstance(value, int):
            raise NotImplementedError(_('Operation not supported.'))
        fleet_models = self.env['fleet.vehicle.model'].search([])
        if operator == '=':
            fleet_models = fleet_models.filtered(lambda m: m.vehicle_count == value)
        elif operator == '!=':
            fleet_models = fleet_models.filtered(lambda m: m.vehicle_count != value)
        elif operator == '<':
            fleet_models = fleet_models.filtered(lambda m: m.vehicle_count < value)
        elif operator == '>':
            fleet_models = fleet_models.filtered(lambda m: m.vehicle_count > value)
        return [('id', 'in', fleet_models.ids)]

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
