# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import _, api, fields, models
from odoo.fields import Domain


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

    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(1970, current_year + 1)]

    name = fields.Char('Model name', required=True, tracking=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True, tracking=True, index='btree_not_null')
    category_id = fields.Many2one('fleet.vehicle.model.category', 'Category', tracking=True)
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    image_128 = fields.Image(related='brand_id.image_128', readonly=True)
    active = fields.Boolean(default=True)
    vehicle_type = fields.Selection([('car', 'Car'), ('bike', 'Bike')], default='car', required=True, tracking=True)
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], 'Transmission', tracking=True)
    vehicle_count = fields.Integer(compute='_compute_vehicle_count', search='_search_vehicle_count')
    model_year = fields.Selection(selection='_get_year_selection', tracking=True)
    color = fields.Char(tracking=True)
    seats = fields.Integer(string='Seating Capacity', tracking=True)
    doors = fields.Integer(string='Number of Doors', tracking=True,
        help="Specifies the total number of doors, including the truck and hatch doors, if applicable.")
    trailer_hook = fields.Boolean(default=False, string='Trailer Hitch', tracking=True,
        help="A trailer hitch is a device attached to a vehicle's chassis for towing purposes,\
            such as pulling trailers, boats, or other vehicles.")
    default_co2 = fields.Float('CO₂ Emissions', tracking=True)
    co2_emission_unit = fields.Selection([('g/km', 'g/km'), ('g/mi', 'g/mi')], compute='_compute_co2_emission_unit', required=True)
    co2_standard = fields.Char(string="Emission Standard", tracking=True,
        help='''Emission Standard specifies the regulatory test procedure or \
            guideline under which a vehicle's emissions are measured.''')
    default_fuel_type = fields.Selection(FUEL_TYPES, 'Fuel Type', default='electric', tracking=True)
    power = fields.Float('Power', tracking=True)
    horsepower = fields.Float(tracking=True)
    horsepower_tax = fields.Float('Horsepower Taxation', tracking=True)
    electric_assistance = fields.Boolean(default=False, tracking=True)
    power_unit = fields.Selection([
        ('power', 'kW'),
        ('horsepower', 'Horsepower (hp)')
        ], 'Power Unit', default='power', required=True)
    vehicle_properties_definition = fields.PropertiesDefinition('Vehicle Properties')
    vehicle_range = fields.Integer(string="Range")
    range_unit = fields.Selection([('km', 'km'), ('mi', 'mi')], default="km", required=True)
    drive_type = fields.Selection([
        ('fwd', 'Front-Wheel Drive (FWD)'),
        ('awd', 'All-Wheel Drive (AWD)'),
        ('rwd', 'Rear-Wheel Drive (RWD)'),
        ('4wd', 'Four-Wheel Drive (4WD)'),
    ])

    @api.model
    def _search_display_name(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return ['|', ('name', operator, value), ('brand_id.name', operator, value)]

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

    @api.depends('range_unit')
    def _compute_co2_emission_unit(self):
        for record in self:
            if record.range_unit == 'km':
                record.co2_emission_unit = 'g/km'
            else:
                record.co2_emission_unit = 'g/mi'

    @api.model
    def _search_vehicle_count(self, operator, value):
        fleet_models = self.env['fleet.vehicle.model'].search_fetch([], ['vehicle_count'])
        fleet_models = fleet_models.filtered_domain([('vehicle_count', operator, value)])
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
