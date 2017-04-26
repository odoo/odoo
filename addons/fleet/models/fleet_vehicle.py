# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class FleetVehicle(models.Model):
    _inherit = 'mail.thread'
    _name = 'fleet.vehicle'
    _description = 'Information on a vehicle'
    _order = 'license_plate asc'

    def _get_default_state(self):
        state = self.env.ref('fleet.vehicle_state_active', raise_if_not_found=False)
        return state and state.id or False

    name = fields.Char(compute="_compute_vehicle_name", store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', 'Company')
    license_plate = fields.Char(required=True, help='License plate number of the vehicle (i = plate number for a car)')
    vin_sn = fields.Char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)', copy=False)
    driver_id = fields.Many2one('res.partner', 'Driver', help='Driver of the vehicle')
    model_id = fields.Many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle')
    log_fuel = fields.One2many('fleet.vehicle.log.fuel', 'vehicle_id', 'Fuel Logs')
    log_services = fields.One2many('fleet.vehicle.log.services', 'vehicle_id', 'Services Logs')
    log_contracts = fields.One2many('fleet.vehicle.log.contract', 'vehicle_id', 'Contracts')
    cost_count = fields.Integer(compute="_compute_count_all", string="Costs")
    contract_count = fields.Integer(compute="_compute_count_all", string='Contracts')
    service_count = fields.Integer(compute="_compute_count_all", string='Services')
    fuel_logs_count = fields.Integer(compute="_compute_count_all", string='Fuel Logs')
    odometer_count = fields.Integer(compute="_compute_count_all", string='Odometer')
    acquisition_date = fields.Date('Immatriculation Date', required=False, help='Date when the vehicle has been immatriculated')
    color = fields.Char(help='Color of the vehicle')
    state_id = fields.Many2one('fleet.vehicle.state', 'State', default=_get_default_state, help='Current state of the vehicle', ondelete="set null")
    location = fields.Char(help='Location of the vehicle (garage, ...)')
    seats = fields.Integer('Seats Number', help='Number of seats of the vehicle')
    doors = fields.Integer('Doors Number', help='Number of doors of the vehicle', default=5)
    tag_ids = fields.Many2many('fleet.vehicle.tag', 'fleet_vehicle_vehicle_tag_rel', 'vehicle_tag_id', 'tag_id', 'Tags', copy=False)
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Last Odometer',
        help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection([
        ('kilometers', 'Kilometers'),
        ('miles', 'Miles')
        ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ', required=True)
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], 'Transmission', help='Transmission Used by the vehicle')
    fuel_type = fields.Selection([
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid')
        ], 'Fuel Type', help='Fuel Used by the vehicle')
    horsepower = fields.Integer()
    horsepower_tax = fields.Float('Horsepower Taxation')
    power = fields.Integer('Power', help='Power in kW of the vehicle')
    co2 = fields.Float('CO2 Emissions', help='CO2 emissions of the vehicle')
    image = fields.Binary(related='model_id.image', string="Logo")
    image_medium = fields.Binary(related='model_id.image_medium', string="Logo (medium)")
    image_small = fields.Binary(related='model_id.image_small', string="Logo (small)")
    contract_renewal_due_soon = fields.Boolean(compute='_compute_contract_reminder', search='_search_contract_renewal_due_soon',
        string='Has Contracts to renew', multi='contract_info')
    contract_renewal_overdue = fields.Boolean(compute='_compute_contract_reminder', search='_search_get_overdue_contract_reminder',
        string='Has Contracts Overdue', multi='contract_info')
    contract_renewal_name = fields.Text(compute='_compute_contract_reminder', string='Name of contract to renew soon', multi='contract_info')
    contract_renewal_total = fields.Text(compute='_compute_contract_reminder', string='Total of contracts due or overdue minus one',
        multi='contract_info')
    car_value = fields.Float(string="Catalog Value (VAT incl.)", help='Value of the bought vehicle')
    residual_value = fields.Float()

    _sql_constraints = [
        ('driver_id_unique', 'UNIQUE(driver_id)', 'Only one car can be assigned to the same employee!')
    ]

    @api.depends('model_id', 'license_plate')
    def _compute_vehicle_name(self):
        for record in self:
            record.name = record.model_id.brand_id.name + '/' + record.model_id.name + '/' + record.license_plate

    def _get_odometer(self):
        FleetVehicalOdometer = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = FleetVehicalOdometer.search([('vehicle_id', '=', record.id)], limit=1, order='value desc')
            if vehicle_odometer:
                record.odometer = vehicle_odometer.value
            else:
                record.odometer = 0

    def _set_odometer(self):
        for record in self:
            if record.odometer:
                date = fields.Date.context_today(record)
                data = {'value': record.odometer, 'date': date, 'vehicle_id': record.id}
                self.env['fleet.vehicle.odometer'].create(data)

    def _compute_count_all(self):
        Odometer = self.env['fleet.vehicle.odometer']
        LogFuel = self.env['fleet.vehicle.log.fuel']
        LogService = self.env['fleet.vehicle.log.services']
        LogContract = self.env['fleet.vehicle.log.contract']
        Cost = self.env['fleet.vehicle.cost']
        for record in self:
            record.odometer_count = Odometer.search_count([('vehicle_id', '=', record.id)])
            record.fuel_logs_count = LogFuel.search_count([('vehicle_id', '=', record.id)])
            record.service_count = LogService.search_count([('vehicle_id', '=', record.id)])
            record.contract_count = LogContract.search_count([('vehicle_id', '=', record.id), ('state', '=', 'open')])
            record.cost_count = Cost.search_count([('vehicle_id', '=', record.id), ('parent_id', '=', False)])

    @api.depends('log_contracts')
    def _compute_contract_reminder(self):
        for record in self:
            overdue = False
            due_soon = False
            total = 0
            name = ''
            for element in record.log_contracts:
                if element.state in ('open', 'toclose') and element.expiration_date:
                    current_date_str = fields.Date.context_today(record)
                    due_time_str = element.expiration_date
                    current_date = fields.Date.from_string(current_date_str)
                    due_time = fields.Date.from_string(due_time_str)
                    diff_time = (due_time - current_date).days
                    if diff_time < 0:
                        overdue = True
                        total += 1
                    if diff_time < 15 and diff_time >= 0:
                            due_soon = True
                            total += 1
                    if overdue or due_soon:
                        log_contract = self.env['fleet.vehicle.log.contract'].search([
                            ('vehicle_id', '=', record.id),
                            ('state', 'in', ('open', 'toclose'))
                            ], limit=1, order='expiration_date asc')
                        if log_contract:
                            # we display only the name of the oldest overdue/due soon contract
                            name = log_contract.cost_subtype_id.name

            record.contract_renewal_overdue = overdue
            record.contract_renewal_due_soon = due_soon
            record.contract_renewal_total = total - 1  # we remove 1 from the real total for display purposes
            record.contract_renewal_name = name

    def _search_contract_renewal_due_soon(self, operator, value):
        res = []
        assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        datetime_today = fields.Datetime.from_string(today)
        limit_date = fields.Datetime.to_string(datetime_today + relativedelta(days=+15))
        self.env.cr.execute("""SELECT cost.vehicle_id,
                        count(contract.id) AS contract_number
                        FROM fleet_vehicle_cost cost
                        LEFT JOIN fleet_vehicle_log_contract contract ON contract.cost_id = cost.id
                        WHERE contract.expiration_date IS NOT NULL
                          AND contract.expiration_date > %s
                          AND contract.expiration_date < %s
                          AND contract.state IN ('open', 'toclose')
                        GROUP BY cost.vehicle_id""", (today, limit_date))
        res_ids = [x[0] for x in self.env.cr.fetchall()]
        res.append(('id', search_operator, res_ids))
        return res

    def _search_get_overdue_contract_reminder(self, operator, value):
        res = []
        assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        self.env.cr.execute('''SELECT cost.vehicle_id,
                        count(contract.id) AS contract_number
                        FROM fleet_vehicle_cost cost
                        LEFT JOIN fleet_vehicle_log_contract contract ON contract.cost_id = cost.id
                        WHERE contract.expiration_date IS NOT NULL
                          AND contract.expiration_date < %s
                          AND contract.state IN ('open', 'toclose')
                        GROUP BY cost.vehicle_id ''', (today,))
        res_ids = [x[0] for x in self.env.cr.fetchall()]
        res.append(('id', search_operator, res_ids))
        return res

    @api.onchange('model_id')
    def _onchange_model(self):
        if self.model_id:
            self.image_medium = self.model_id.image
        else:
            self.image_medium = False

    @api.model
    def create(self, data):
        vehicle = super(FleetVehicle, self.with_context(mail_create_nolog=True)).create(data)
        vehicle.message_post(body=_('%s %s has been added to the fleet!') % (vehicle.model_id.name, vehicle.license_plate))
        return vehicle

    @api.multi
    def write(self, vals):
        """
        This function write an entry in the openchatter whenever we change important information
        on the vehicle like the model, the drive, the state of the vehicle or its license plate
        """
        for vehicle in self:
            changes = []
            if 'model_id' in vals and vehicle.model_id.id != vals['model_id']:
                value = self.env['fleet.vehicle.model'].browse(vals['model_id']).name
                oldmodel = vehicle.model_id.name or _('None')
                changes.append(_("Model: from '%s' to '%s'") % (oldmodel, value))
            if 'driver_id' in vals and vehicle.driver_id.id != vals['driver_id']:
                value = self.env['res.partner'].browse(vals['driver_id']).name
                olddriver = (vehicle.driver_id.name) or _('None')
                changes.append(_("Driver: from '%s' to '%s'") % (olddriver, value))
            if 'state_id' in vals and vehicle.state_id.id != vals['state_id']:
                value = self.env['fleet.vehicle.state'].browse(vals['state_id']).name
                oldstate = vehicle.state_id.name or _('None')
                changes.append(_("State: from '%s' to '%s'") % (oldstate, value))
            if 'license_plate' in vals and vehicle.license_plate != vals['license_plate']:
                old_license_plate = vehicle.license_plate or _('None')
                changes.append(_("License Plate: from '%s' to '%s'") % (old_license_plate, vals['license_plate']))

            if len(changes) > 0:
                self.message_post(body=", ".join(changes))

            return super(FleetVehicle, self).write(vals)

    @api.multi
    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window'].for_xml_id('fleet', xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False

    @api.multi
    def act_show_log_cost(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('fleet', 'fleet_vehicle_costs_action')
        res.update(
            context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id)]
        )
        return res


class FleetVehicleOdometer(models.Model):
    _name = 'fleet.vehicle.odometer'
    _description = 'Odometer log for a vehicle'
    _order = 'date desc'

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float('Odometer Value', group_operator="max")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver")

    @api.depends('vehicle_id', 'date')
    def _compute_vehicle_log_name(self):
        for record in self:
            name = record.vehicle_id.name
            if not name:
                name = record.date
            elif record.date:
                name += ' / ' + record.date
            self.name = name

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.unit = self.vehicle_id.odometer_unit


class FleetVehicleState(models.Model):
    _name = 'fleet.vehicle.state'
    _order = 'sequence asc'

    name = fields.Char(required=True)
    sequence = fields.Integer(help="Used to order the note stages")

    _sql_constraints = [('fleet_state_name_unique', 'unique(name)', 'State name already exists')]


class FleetVehicleTag(models.Model):
    _name = 'fleet.vehicle.tag'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer('Color Index', default=10)

    _sql_constraints = [('name_uniq', 'unique (name)', "Tag name already exists !")]


class FleetServiceType(models.Model):
    _name = 'fleet.service.type'
    _description = 'Type of services available on a vehicle'

    name = fields.Char(required=True, translate=True)
    category = fields.Selection([
        ('contract', 'Contract'),
        ('service', 'Service'),
        ('both', 'Both')
        ], 'Category', required=True, help='Choose wheter the service refer to contracts, vehicle services or both')
