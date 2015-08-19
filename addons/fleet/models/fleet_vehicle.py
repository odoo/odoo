# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class FleetVehicle(models.Model):

    _name = 'fleet.vehicle'
    _description = 'Information on a vehicle'
    _order = 'license_plate asc'
    _inherit = 'mail.thread'

    @api.model
    def default_stage(self):
        try:
            stage = self.env.ref('fleet.vehicle_stage_active')
        except ValueError:
            stage = False
        return stage

    name = fields.Char(compute='_compute_vehicle_name', store=True)
    company_id = fields.Many2one('res.company', string='Company')
    license_plate = fields.Char(required=True, track_visibility='onchange',
                                help='License plate number of the vehicle (ie: plate number for a car)')
    vin_sn = fields.Char(string='Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)',
                         copy=False)
    driver_id = fields.Many2one('res.partner', string='Driver', track_visibility='onchange',
                                help='Driver of the vehicle')
    model_id = fields.Many2one('fleet.vehicle.model', string='Model', required=True, track_visibility='onchange',
                               help='Model of the vehicle')
    log_fuel_ids = fields.One2many('fleet.vehicle.log.fuel', 'vehicle_id', string='Fuel Logs', oldname='log_fuel')
    log_services_ids = fields.One2many('fleet.vehicle.log.services', 'vehicle_id', string='Services Logs', oldname='log_services')
    log_contracts_ids = fields.One2many('fleet.vehicle.log.contract', 'vehicle_id', string='Contracts', oldname='log_contracts')
    cost_count = fields.Integer(compute='_compute_count_all', string="Costs")
    contract_count = fields.Integer(compute='_compute_count_all', string='Contracts')
    service_count = fields.Integer(compute='_compute_count_all', string='Services')
    fuel_logs_count = fields.Integer(compute='_compute_count_all', string='Fuel Logs')
    odometer_count = fields.Integer(compute='_compute_count_all', string='Odometer')
    acquisition_date = fields.Date(help='Date when the vehicle has been bought')
    color = fields.Char(help='Color of the vehicle')
    stage_id = fields.Many2one('fleet.vehicle.stage', string='Stage', oldname='state_id', track_visibility='onchange',
                               help='Current state of the vehicle', default=default_stage)
    location = fields.Char(help='Location of the vehicle (garage, ...)')
    seats = fields.Integer(string='Seats Number', help='Number of seats of the vehicle')
    doors = fields.Integer(string='Doors Number', help='Number of doors of the vehicle', default=5)
    tag_ids = fields.Many2many('fleet.vehicle.tag', 'fleet_vehicle_vehicle_tag_rel', 'vehicle_tag_id', 'tag_id',
                               string='Tags', copy=False)
    odometer = fields.Float(compute='_compute_get_odometer', inverse='_compute_set_odometer', string='Last Odometer',
                            help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection(selection=[('kilometers', 'Kilometers'), ('miles', 'Miles')],
                                     help='Unit of the odometer',
                                     required=True, default='kilometers')
    transmission = fields.Selection(selection=[('manual', 'Manual'), ('automatic', 'Automatic')],
                                    help='Transmission Used by the vehicle')
    fuel_type = fields.Selection(selection=[('gasoline', 'Gasoline'), ('diesel', 'Diesel'),
                                            ('electric', 'Electric'), ('hybrid', 'Hybrid')],
                                 help='Fuel Used by the vehicle')
    horsepower = fields.Integer()
    horsepower_tax = fields.Float(string='Horsepower Taxation')
    power = fields.Integer(help='Power in kW of the vehicle')
    co2 = fields.Float(string='CO2 Emissions', help='CO2 emissions of the vehicle')
    image = fields.Binary(related='model_id.make_id.image', string="Logo", store=True)
    image_medium = fields.Binary(related='model_id.make_id.image_medium', string="Logo (medium)", store=True)
    image_small = fields.Binary(related='model_id.make_id.image_small', string="Logo (small)", store=True)
    contract_renewal_due_soon = fields.Boolean(compute='_compute_get_contract_reminder',
                                               search='_search_contract_renewal_due_soon',
                                               string='Has Contracts to renew')
    contract_renewal_overdue = fields.Boolean(compute='_compute_get_contract_reminder',
                                              search='_search_get_overdue_contract_reminder',
                                              string='Has Contracts Overdue')
    contract_renewal_name = fields.Text(compute='_compute_get_contract_reminder', string='Name of contract to renew soon')
    contract_renewal_total = fields.Integer(compute='_compute_get_contract_reminder',
                                            string='Total of contracts due or overdue minus one')
    car_value = fields.Float(help='Value of the bought vehicle')

    _sql_constraints = [('unique_chassis_number', 'unique(vin_sn)', 'Same Chassis Number is already exists.')]

    @api.one
    @api.depends('license_plate')
    def _compute_vehicle_name(self):
        self.name = self.model_id.make_id.name + ' / ' + self.model_id.name + ' / ' + self.license_plate

    @api.multi
    def _compute_get_contract_reminder(self):
        LogContract = self.env['fleet.vehicle.log.contract']
        for vehicle in self:
            overdue = False
            due_soon = False
            total = 0
            name = ''
            for contract in vehicle.log_contracts_ids.filtered(lambda contract: contract.state in ('open', 'toclose') and contract.expiration_date):
                current_date = fields.Datetime.from_string(fields.Date.context_today(self))
                due_time = fields.Datetime.from_string(contract.expiration_date)
                diff_time = (due_time-current_date).days
                if diff_time < 0:
                    overdue = True
                    total += 1
                if diff_time < 15 and diff_time >= 0:
                    due_soon = True
                    total += 1
                if overdue or due_soon:
                    log_contract = LogContract.search([('vehicle_id', '=', vehicle.id),
                                                     ('state', 'in', ('open', 'toclose'))],
                                                    limit=1, order='expiration_date asc')
                    if log_contract:
                        # we display only the name of the oldest overdue/due soon contract
                        name = log_contract.cost_subtype_id.name

            vehicle.contract_renewal_overdue = overdue
            vehicle.contract_renewal_due_soon = due_soon
            vehicle.contract_renewal_total = (total - 1)  # we remove 1 from the real total for display purposes
            vehicle.contract_renewal_name = name

    @api.multi
    def _compute_count_all(self):
        Odometer = self.env['fleet.vehicle.odometer']
        LogFuel = self.env['fleet.vehicle.log.fuel']
        LogService = self.env['fleet.vehicle.log.services']
        LogContract = self.env['fleet.vehicle.log.contract']
        VehicleCost = self.env['fleet.vehicle.cost']
        for vehicle in self:
            odometer_count = Odometer.read_group([('vehicle_id', '=', vehicle.id)], fields=['vehicle_id'], groupby=['vehicle_id'])
            vehicle.odometer_count = odometer_count and odometer_count[0]['vehicle_id_count']
            fuel_logs_count = LogFuel.read_group([('vehicle_id', '=', vehicle.id)], fields=['vehicle_id'], groupby=['vehicle_id'])
            vehicle.fuel_logs_count = fuel_logs_count and fuel_logs_count[0]['vehicle_id_count']
            service_count = LogService.read_group([('vehicle_id', '=', vehicle.id)], fields=['vehicle_id'], groupby=['vehicle_id'])
            vehicle.service_count = service_count and service_count[0]['vehicle_id_count']
            contract_count = LogContract.read_group([('vehicle_id', '=', vehicle.id)], fields=['vehicle_id'], groupby=['vehicle_id'])
            vehicle.contract_count = contract_count and contract_count[0]['vehicle_id_count']
            cost_count = VehicleCost.read_group([('vehicle_id', '=', vehicle.id), ('parent_id', '=', False)], fields=['vehicle_id'], groupby=['vehicle_id'])
            vehicle.cost_count = cost_count and cost_count[0]['vehicle_id_count']

    @api.one
    def _compute_get_odometer(self):
        vehicle_odometer = self.env['fleet.vehicle.odometer'].search([('vehicle_id', '=', self.id)], limit=1, order='value desc')
        if vehicle_odometer:
            self.odometer = vehicle_odometer.value

    @api.one
    def _compute_set_odometer(self):
        if self.odometer:
            return self.env['fleet.vehicle.odometer'].create({'value': self.odometer,
                                                              'date': fields.Date.context_today(self),
                                                              'vehicle_id': self.id
                                                              })

    @api.model
    def create(self, values):
        vehicle = super(FleetVehicle, self).create(values)
        vehicle.message_post(body=_('%s %s has been added to the fleet!') % (vehicle.model_id.name,
                             vehicle.license_plate))
        return vehicle

    @api.multi
    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        if self.env.context.get('xml_id'):
            result = self.env.ref('fleet.' + self.env.context['xml_id']).read()[0]
            result['context'] = dict(self.env.context, default_vehicle_id=self.id)
            result['domain'] = [('vehicle_id', '=', self.id)]
            return result
        return False

    @api.multi
    def act_show_log_cost(self):
        """ This opens log view to view and add new log for this vehicle,
            groupBy default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        result = self.env.ref('fleet.fleet_vehicle_costs_act').read()[0]
        result['context'] = dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True)
        result['domain'] = [('vehicle_id', '=', self.id)]
        return result

    @api.model
    def _search_get_overdue_contract_reminder(self, operator, value):
        if not (operator in ('=', '!=', '<>') and value in (True, False)):
            raise UserError(_("Operation not supported"))
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        overdue_contracts = self.env['fleet.vehicle.log.contract'].search([('expiration_date', '<', today), ('state', 'in', ('open', 'toclose'))])
        overdue_contract_vehicle = [contract.vehicle_id.id for contract in overdue_contracts]
        return [('id', search_operator, overdue_contract_vehicle)]

    @api.model
    def _search_contract_renewal_due_soon(self, operator, value):
        if not (operator in ('=', '!=', '<>') and value in (True, False)):
            raise UserError(_("Operation not supported"))
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        datetime_today = fields.Datetime.from_string(today)
        limit_date = fields.Date.to_string(datetime_today + relativedelta(days=+15))
        renewal_contracts = self.env['fleet.vehicle.log.contract'].search([('expiration_date', '>', today),
                                                                         ('expiration_date', '<', limit_date), ('state', 'in', ('open', 'toclose'))])
        renewal_contract_vehicle = [contract.vehicle_id.id for contract in renewal_contracts]
        return [('id', search_operator, renewal_contract_vehicle)]
