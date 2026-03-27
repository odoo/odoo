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
    _inherit = ['mail.thread', 'mail.activity.mixin', 'avatar.mixin']
    _description = 'Model of a vehicle'
    _order = 'name asc'

    name = fields.Char('Model name', required=True, tracking=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True, tracking=True)
    category_id = fields.Many2one('fleet.vehicle.model.category', 'Category', tracking=True)
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    image_128 = fields.Image(related='brand_id.image_128', readonly=True)
    active = fields.Boolean(default=True)
    vehicle_type = fields.Selection([('car', 'Car'), ('bike', 'Bike')], default='car', required=True, tracking=True)
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], 'Transmission', tracking=True)
    vehicle_count = fields.Integer(compute='_compute_vehicle_count', search='_search_vehicle_count')
    model_year = fields.Integer(tracking=True)
    color = fields.Char(tracking=True)
    seats = fields.Integer(string='Seats Number', tracking=True)
    doors = fields.Integer(string='Doors Number', tracking=True)
    trailer_hook = fields.Boolean(default=False, string='Trailer Hitch', tracking=True)
    default_co2 = fields.Float('CO2 Emissions', tracking=True)
    co2_standard = fields.Char(tracking=True)
    default_fuel_type = fields.Selection(FUEL_TYPES, 'Fuel Type', default='electric', tracking=True)
    power = fields.Integer('Power', tracking=True)
    horsepower = fields.Integer(tracking=True)
    horsepower_tax = fields.Float('Horsepower Taxation', tracking=True)
    electric_assistance = fields.Boolean(default=False, tracking=True)
    power_unit = fields.Selection([
        ('power', 'kW'),
        ('horsepower', 'Horsepower')
        ], 'Power Unit', default='power', required=True)
    vehicle_properties_definition = fields.PropertiesDefinition('Vehicle Properties')
    vehicle_range = fields.Integer(string="Range")

    @api.model
    def _search_display_name(self, operator, value):
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            positive_operator = expression.TERM_OPERATORS_NEGATION[operator]
        else:
            positive_operator = operator
        domain = expression.OR([[('name', positive_operator, value)], [('brand_id.name', positive_operator, value)]])
        if positive_operator != operator:
            domain = ['!', *domain]
        return domain

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
        context = {'default_model_id': self.id}
        if self.vehicle_count:
            view_mode = 'kanban,list,form'
            name = _('Vehicles')
            context['search_default_model_id'] = self.id
        else:
            view_mode = 'form'
            name = _('Vehicle')
        view = {
            'type': 'ir.actions.act_window',
            'view_mode': view_mode,
            'res_model': 'fleet.vehicle',
            'name': name,
            'context': context,
        }

        return view
