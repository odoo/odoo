# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.osv import expression


class FleetVehicle(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'fleet.vehicle'
    _description = 'Vehicle'
    _order = 'license_plate asc, acquisition_date asc'

    def _get_default_state(self):
        state = self.env.ref('fleet.fleet_vehicle_state_registered', raise_if_not_found=False)
        return state if state and state.id else False

    name = fields.Char(compute="_compute_vehicle_name", store=True)
    description = fields.Text("Vehicle Description")
    active = fields.Boolean('Active', default=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    license_plate = fields.Char(tracking=True,
        help='License plate number of the vehicle (i = plate number for a car)')
    vin_sn = fields.Char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)', copy=False)
    driver_id = fields.Many2one('res.partner', 'Driver', tracking=True, help='Driver of the vehicle', copy=False)
    future_driver_id = fields.Many2one('res.partner', 'Future Driver', tracking=True, help='Next Driver of the vehicle', copy=False, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    model_id = fields.Many2one('fleet.vehicle.model', 'Model',
        tracking=True, required=True, help='Model of the vehicle')
    manager_id = fields.Many2one('res.users', compute='_compute_manager_id', domain=lambda self: [('groups_id', 'in', self.env.ref('fleet.fleet_group_manager').id)], store=True, readonly=False)

    @api.depends('model_id')
    def _compute_manager_id(self):
        if self.model_id:
            self.manager_id = self.model_id.manager_id
        else:
            self.manager_id = None

    brand_id = fields.Many2one('fleet.vehicle.model.brand', 'Brand', related="model_id.brand_id", store=True, readonly=False)
    log_drivers = fields.One2many('fleet.vehicle.assignation.log', 'vehicle_id', string='Assignment Logs')
    log_services = fields.One2many('fleet.vehicle.log.services', 'vehicle_id', 'Services Logs')
    log_contracts = fields.One2many('fleet.vehicle.log.contract', 'vehicle_id', 'Contracts')
    contract_count = fields.Integer(compute="_compute_count_all", string='Contract Count')
    service_count = fields.Integer(compute="_compute_count_all", string='Services')
    odometer_count = fields.Integer(compute="_compute_count_all", string='Odometer')
    history_count = fields.Integer(compute="_compute_count_all", string="Drivers History Count")
    next_assignation_date = fields.Date('Assignment Date', help='This is the date at which the car will be available, if not set it means available instantly')
    acquisition_date = fields.Date('Immatriculation Date', required=False,
        default=fields.Date.today, help='Date when the vehicle has been immatriculated')
    first_contract_date = fields.Date(string="First Contract Date", default=fields.Date.today)
    color = fields.Char(help='Color of the vehicle')
    state_id = fields.Many2one('fleet.vehicle.state', 'State',
        default=_get_default_state, group_expand='_read_group_stage_ids',
        tracking=True,
        help='Current state of the vehicle', ondelete="set null")
    location = fields.Char(help='Location of the vehicle (garage, ...)')
    seats = fields.Integer('Seats Number', help='Number of seats of the vehicle')
    model_year = fields.Char('Model Year', help='Year of the model')
    doors = fields.Integer('Doors Number', help='Number of doors of the vehicle', default=5)
    tag_ids = fields.Many2many('fleet.vehicle.tag', 'fleet_vehicle_vehicle_tag_rel', 'vehicle_tag_id', 'tag_id', 'Tags', copy=False)
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Last Odometer',
        help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi')
        ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ', required=True)
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], 'Transmission', help='Transmission Used by the vehicle')
    fuel_type = fields.Selection([
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('lpg', 'LPG'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid')
        ], 'Fuel Type', help='Fuel Used by the vehicle')
    horsepower = fields.Integer()
    horsepower_tax = fields.Float('Horsepower Taxation')
    power = fields.Integer('Power', help='Power in kW of the vehicle')
    co2 = fields.Float('CO2 Emissions', help='CO2 emissions of the vehicle')
    image_128 = fields.Image(related='model_id.image_128', readonly=True)
    contract_renewal_due_soon = fields.Boolean(compute='_compute_contract_reminder', search='_search_contract_renewal_due_soon',
        string='Has Contracts to renew')
    contract_renewal_overdue = fields.Boolean(compute='_compute_contract_reminder', search='_search_get_overdue_contract_reminder',
        string='Has Contracts Overdue')
    contract_renewal_name = fields.Text(compute='_compute_contract_reminder', string='Name of contract to renew soon')
    contract_renewal_total = fields.Text(compute='_compute_contract_reminder', string='Total of contracts due or overdue minus one')
    car_value = fields.Float(string="Catalog Value (VAT Incl.)", help='Value of the bought vehicle')
    net_car_value = fields.Float(string="Purchase Value", help="Purchase value of the vehicle")
    residual_value = fields.Float()
    plan_to_change_car = fields.Boolean(related='driver_id.plan_to_change_car', store=True, readonly=False)
    vehicle_type = fields.Selection(related='model_id.vehicle_type')

    @api.depends('model_id.brand_id.name', 'model_id.name', 'license_plate')
    def _compute_vehicle_name(self):
        for record in self:
            record.name = (record.model_id.brand_id.name or '') + '/' + (record.model_id.name or '') + '/' + (record.license_plate or _('No Plate'))

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
        LogService = self.env['fleet.vehicle.log.services']
        LogContract = self.env['fleet.vehicle.log.contract']
        for record in self:
            record.odometer_count = Odometer.search_count([('vehicle_id', '=', record.id)])
            record.service_count = LogService.search_count([('vehicle_id', '=', record.id)])
            record.contract_count = LogContract.search_count([('vehicle_id', '=', record.id), ('state', '!=', 'closed')])
            record.history_count = self.env['fleet.vehicle.assignation.log'].search_count([('vehicle_id', '=', record.id)])

    @api.depends('log_contracts')
    def _compute_contract_reminder(self):
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        for record in self:
            overdue = False
            due_soon = False
            total = 0
            name = ''
            for element in record.log_contracts:
                if element.state in ('open', 'expired') and element.expiration_date:
                    current_date_str = fields.Date.context_today(record)
                    due_time_str = element.expiration_date
                    current_date = fields.Date.from_string(current_date_str)
                    due_time = fields.Date.from_string(due_time_str)
                    diff_time = (due_time - current_date).days
                    if diff_time < 0:
                        overdue = True
                        total += 1
                    if diff_time < delay_alert_contract:
                        due_soon = True
                        total += 1
                    if overdue or due_soon:
                        log_contract = self.env['fleet.vehicle.log.contract'].search([
                            ('vehicle_id', '=', record.id),
                            ('state', 'in', ('open', 'expired'))
                            ], limit=1, order='expiration_date asc')
                        if log_contract:
                            # we display only the name of the oldest overdue/due soon contract
                            name = log_contract.name

            record.contract_renewal_overdue = overdue
            record.contract_renewal_due_soon = due_soon
            record.contract_renewal_total = total - 1  # we remove 1 from the real total for display purposes
            record.contract_renewal_name = name

    def _get_analytic_name(self):
        # This function is used in fleet_account and is overrided in l10n_be_hr_payroll_fleet
        return self.license_plate or _('No plate')

    def _search_contract_renewal_due_soon(self, operator, value):
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        res = []
        assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.context_today(self)
        datetime_today = fields.Datetime.from_string(today)
        limit_date = fields.Datetime.to_string(datetime_today + relativedelta(days=+delay_alert_contract))
        res_ids = self.env['fleet.vehicle.log.contract'].search([
            ('expiration_date', '>', today),
            ('expiration_date', '<', limit_date),
            ('state', 'in', ['open', 'expired'])
        ]).mapped('id')
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
        res_ids = self.env['fleet.vehicle.log.contract'].search([
            ('expiration_date', '!=', False),
            ('expiration_date', '<', today),
            ('state', 'in', ['open', 'expired'])
        ]).mapped('id')
        res.append(('id', search_operator, res_ids))
        return res

    @api.model
    def create(self, vals):
        # Fleet administrator may not have rights to create the plan_to_change_car value when the driver_id is a res.user
        # This trick is used to prevent access right error.
        ptc_value = 'plan_to_change_car' in vals.keys() and {'plan_to_change_car': vals.pop('plan_to_change_car')}
        res = super(FleetVehicle, self).create(vals)
        if ptc_value:
            res.sudo().write(ptc_value)
        if 'driver_id' in vals and vals['driver_id']:
            res.create_driver_history(vals['driver_id'])
        if 'future_driver_id' in vals and vals['future_driver_id']:
            state_waiting_list = self.env.ref('fleet.fleet_vehicle_state_waiting_list', raise_if_not_found=False)
            states = res.mapped('state_id').ids
            if not state_waiting_list or state_waiting_list.id not in states:
                future_driver = self.env['res.partner'].browse(vals['future_driver_id'])
                future_driver.sudo().write({'plan_to_change_car': True})
        return res

    def write(self, vals):
        if 'driver_id' in vals and vals['driver_id']:
            driver_id = vals['driver_id']
            self.filtered(lambda v: v.driver_id.id != driver_id).create_driver_history(driver_id)

        if 'future_driver_id' in vals and vals['future_driver_id']:
            state_waiting_list = self.env.ref('fleet.fleet_vehicle_state_waiting_list', raise_if_not_found=False)
            states = self.mapped('state_id').ids if 'state_id' not in vals else [vals['state_id']]
            if not state_waiting_list or state_waiting_list.id not in states:
                future_driver = self.env['res.partner'].browse(vals['future_driver_id'])
                future_driver.sudo().write({'plan_to_change_car': True})

        res = super(FleetVehicle, self).write(vals)
        if 'active' in vals and not vals['active']:
            self.mapped('log_contracts').write({'active': False})
        return res

    def _close_driver_history(self):
        self.env['fleet.vehicle.assignation.log'].search([
            ('vehicle_id', 'in', self.ids),
            ('driver_id', 'in', self.mapped('driver_id').ids),
            ('date_end', '=', False)
        ]).write({'date_end': fields.Date.today()})

    def create_driver_history(self, driver_id):
        for vehicle in self:
            self.env['fleet.vehicle.assignation.log'].create({
                'vehicle_id': vehicle.id,
                'driver_id': driver_id,
                'date_start': fields.Date.today(),
            })

    def action_accept_driver_change(self):
        self._close_driver_history()
        # Find all the vehicles for which the driver is the future_driver_id
        # remove their driver_id and close their history using current date
        vehicles = self.search([('driver_id', 'in', self.mapped('future_driver_id').ids)])
        vehicles.write({'driver_id': False})
        vehicles._close_driver_history()

        for vehicle in self:
            vehicle.future_driver_id.sudo().write({'plan_to_change_car': False})
            vehicle.driver_id = vehicle.future_driver_id
            vehicle.future_driver_id = False

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env['fleet.vehicle.state'].search([], order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'co2' in fields:
            fields.remove('co2')
        return super(FleetVehicle, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', operator, name), ('driver_id.name', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:

            res = self.env['ir.actions.act_window']._for_xml_id('fleet.%s' % xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False

    def act_show_log_cost(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        copy_context = dict(self.env.context)
        copy_context.pop('group_by', None)
        res = self.env['ir.actions.act_window']._for_xml_id('fleet.fleet_vehicle_costs_action')
        res.update(
            context=dict(copy_context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id)]
        )
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'driver_id' in init_values or 'future_driver_id' in init_values:
            return self.env.ref('fleet.mt_fleet_driver_updated')
        return super(FleetVehicle, self)._track_subtype(init_values)

    def open_assignation_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assignment Logs',
            'view_mode': 'tree',
            'res_model': 'fleet.vehicle.assignation.log',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_driver_id': self.driver_id.id, 'default_vehicle_id': self.id}
        }

class FleetVehicleOdometer(models.Model):
    _name = 'fleet.vehicle.odometer'
    _description = 'Odometer log for a vehicle'
    _order = 'date desc'

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float('Odometer Value', group_operator="max")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver", readonly=False)

    @api.depends('vehicle_id', 'date')
    def _compute_vehicle_log_name(self):
        for record in self:
            name = record.vehicle_id.name
            if not name:
                name = str(record.date)
            elif record.date:
                name += ' / ' + str(record.date)
            record.name = name

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.unit = self.vehicle_id.odometer_unit


class FleetVehicleState(models.Model):
    _name = 'fleet.vehicle.state'
    _order = 'sequence asc'
    _description = 'Vehicle Status'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(help="Used to order the note stages")

    _sql_constraints = [('fleet_state_name_unique', 'unique(name)', 'State name already exists')]


class FleetVehicleTag(models.Model):
    _name = 'fleet.vehicle.tag'
    _description = 'Vehicle Tag'

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [('name_uniq', 'unique (name)', "Tag name already exists !")]


class FleetServiceType(models.Model):
    _name = 'fleet.service.type'
    _description = 'Fleet Service Type'

    name = fields.Char(required=True, translate=True)
    category = fields.Selection([
        ('contract', 'Contract'),
        ('service', 'Service')
        ], 'Category', required=True, help='Choose whether the service refer to contracts, vehicle services or both')


class FleetVehicleAssignationLog(models.Model):
    _name = "fleet.vehicle.assignation.log"
    _description = "Drivers history on a vehicle"
    _order = "create_date desc, date_start desc"

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle", required=True)
    driver_id = fields.Many2one('res.partner', string="Driver", required=True)
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")
