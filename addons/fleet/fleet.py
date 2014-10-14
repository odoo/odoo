# -*- coding: utf-8 -*-
from collections import defaultdict
import datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, tools, _
from openerp.exceptions import UserError


class FleetVehicleCost(models.Model):
    _name = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle'
    _order = 'date desc, vehicle_id asc, id desc'

    name = fields.Char(related='vehicle_id.name', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True,
                                 help='Vehicle concerned by this log')
    cost_subtype_id = fields.Many2one('fleet.service.type', string='Type',
                                      help='Cost type purchased with this cost')
    amount = fields.Float(string='Total Price')
    cost_type = fields.Selection(selection=[('contract', 'Contract'), ('services', 'Services'),
                                            ('fuel', 'Fuel'), ('other', 'Other')],
                                 string='Category of the cost', help='For internal purpose only',
                                 required=True, default='other')
    parent_id = fields.Many2one('fleet.vehicle.cost', string='Parent', help='Parent cost to this current cost')
    cost_ids = fields.One2many('fleet.vehicle.cost', 'parent_id', string='Included Services')
    odometer_id = fields.Many2one('fleet.vehicle.odometer', string='Odometer',
                                  help='Odometer measure of the vehicle at the moment of this log')
    odometer = fields.Float(compute='_compute_get_odometer', inverse='_compute_set_odometer', string='Odometer Value',
                            help='Odometer measure of the vehicle at the moment of this log', store=True)
    odometer_unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    date = fields.Date(help='Date when the cost has been executed')
    contract_id = fields.Many2one('fleet.vehicle.log.contract', string='Contract',
                                  help='Contract attached to this cost')
    auto_generated = fields.Boolean('Automatically Generated', readonly=True, required=True)

    @api.one
    @api.depends('odometer_id')
    def _compute_get_odometer(self):
        self.odometer = self.odometer_id and self.odometer_id.value

    @api.one
    def _compute_set_odometer(self):
        if not self.odometer:
            raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
        odometer = self.env['fleet.vehicle.odometer'].create({
            'value': self.odometer,
            'date': self.date or fields.Date.context_today(self),
            'vehicle_id': self.vehicle_id.id})
        self.odometer_id = odometer.id

    @api.model
    def create(self, values):
        # make sure that the data are consistent with values of parent and contract records given
        if values.get('parent_id'):
            parent = self.browse(values['parent_id'])
            values['vehicle_id'] = parent.vehicle_id.id
            values['date'] = parent.date
            values['cost_type'] = parent.cost_type
        if values.get('contract_id'):
            contract = self.env['fleet.vehicle.log.contract'].browse(values['contract_id'])
            values['vehicle_id'] = contract.vehicle_id.id
            values['cost_subtype_id'] = contract.cost_subtype_id.id
            values['cost_type'] = contract.cost_type
        if 'odometer' in values and not values['odometer']:
            # if received value for odometer is 0, then remove it from the data as it would result to the creation of a
            # odometer log with 0, which is to be avoided
            del(values['odometer'])
        return super(FleetVehicleCost, self).create(values)


class FleetVehicleTag(models.Model):
    _name = 'fleet.vehicle.tag'

    name = fields.Char(required=True, translate=True)


class FleetVehicleStage(models.Model):
    _name = 'fleet.vehicle.stage'
    _order = 'sequence asc, id asc'

    name = fields.Char(required=True)
    sequence = fields.Integer(help="Used to order the vehicle stages")

    _sql_constraints = [('fleet_stage_name_unique', 'unique(name)', _('Stage name already exists'))]


class FleetVehicleModel(models.Model):

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc, id asc'

    @api.multi
    def name_get(self):
        return self.mapped(lambda m: (m.id, '/'.join(filter(None, (m.make_id.name, m.name)))))

    name = fields.Char(store=True, required=True)
    make_id = fields.Many2one('fleet.make', string='Make', oldname='brand_id', required=True, help='Make of the vehicle')
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id')
    image = fields.Binary(related='make_id.image', string="Logo", store=True)
    image_medium = fields.Binary(related='make_id.image_medium', string="Logo (medium)", store=True)
    image_small = fields.Binary(related='make_id.image_small', string="Logo (small)", store=True)


class FleetMake(models.Model):
    _name = 'fleet.make'
    _description = 'Make of the vehicle'
    _order = 'name asc, id asc'

    name = fields.Char(string='Make', required=True)
    image = fields.Binary(string="Logo", help="This field holds the image used as logo for the brand,limited to 1024x1024px.")
    image_medium = fields.Binary(compute='_compute_get_image', inverse='_compute_set_image', string="Medium-sized photo", store=True,
                                 help="Medium-sized logo of the brand. It is automatically "
                                      "resize as a 128x128px image, with aspect ratio preserved. "
                                      "Use this field in form views or some kanban views.")
    image_small = fields.Binary(compute='_compute_get_image', inverse='_compute_set_image', string="Small-sized photo", store=True,
                                help="Small-sized photo of the brand. It is automatically "
                                     "resize as a 64x64px image, with aspect ratio preserved. "
                                     "Use this field anywhere a small image is required.")

    @api.one
    @api.depends('image')
    def _compute_get_image(self):
        make_images = tools.image_get_resized_images(self.image)
        self.image_medium = make_images.get('image_medium')
        self.image_small = make_images.get('image_small')

    @api.one
    def _compute_set_image(self):
        self.image = tools.image_resize_image_big(self.image_medium)


class FleetVehicle(models.Model):

    _name = 'fleet.vehicle'
    _description = 'Information on a vehicle'
    _order = 'license_plate asc'
    _inherit = 'mail.thread'

    @api.model
    def default_stage(self):
        try:
            model_id = self.env.ref('fleet.vehicle_stage_active')
        except ValueError:
            model_id = False
        return model_id

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
    log_fuel = fields.One2many('fleet.vehicle.log.fuel', 'vehicle_id', string='Fuel Logs')
    log_services = fields.One2many('fleet.vehicle.log.services', 'vehicle_id', string='Services Logs')
    log_contracts = fields.One2many('fleet.vehicle.log.contract', 'vehicle_id', string='Contracts')
    cost_count = fields.Integer(compute='_compute_count_all', string="Costs")
    contract_count = fields.Integer(compute='_compute_count_all', string='Contracts')
    service_count = fields.Integer(compute='_compute_count_all', string='Services')
    fuel_logs_count = fields.Integer(compute='_compute_count_all', string='Fuel Logs')
    odometer_count = fields.Integer(compute='_compute_count_all', string='Odometer')
    acquisition_date = fields.Date('Acquisition Date', help='Date when the vehicle has been bought')
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
            for contract in vehicle.log_contracts:
                if contract.state in ('open', 'toclose') and contract.expiration_date:
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
            vehicle.odometer_count = Odometer.search_count([('vehicle_id', '=', vehicle.id)])
            vehicle.fuel_logs_count = LogFuel.search_count([('vehicle_id', '=', vehicle.id)])
            vehicle.service_count = LogService.search_count([('vehicle_id', '=', vehicle.id)])
            vehicle.contract_count = LogContract.search_count([('vehicle_id', '=', vehicle.id)])
            vehicle.cost_count = VehicleCost.search_count([('vehicle_id', '=', vehicle.id), ('parent_id', '=', False)])

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


class FleetVehicleOdometer(models.Model):

    _name = 'fleet.vehicle.odometer'
    _description = 'Odometer log for a vehicle'
    _order = 'date desc'

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float('Odometer Value', group_operator="max")
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', readonly=True)

    @api.one
    @api.depends('vehicle_id', 'date')
    def _compute_vehicle_log_name(self):
        name = self.vehicle_id and self.vehicle_id.name or ''
        self.name = self.date and name + ' / ' + self.date or name


class FleetVehicleLogFuel(models.Model):

    _name = 'fleet.vehicle.log.fuel'
    _description = 'Fuel log for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def _get_default_service_type(self):
        try:
            model_id = self.env.ref('fleet.type_service_refueling')
        except ValueError:
            model_id = False
        return model_id

    liter = fields.Float()
    price_per_liter = fields.Float()
    purchaser_id = fields.Many2one('res.partner', string='Purchaser',
                                   domain="['|', ('customer', '=', True), ('employee', '=', True)]")
    invoice_reference = fields.Char()
    vendor_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', True)]")
    notes = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    date = fields.Date(default=fields.Date.context_today)
    # we need to keep this field as a related with store=True because the graph view doesn't support (1) to address
    # fields from inherited table and (2) fields that aren't stored in database

    _defaults = {
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'fuel',
    }

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.odometer_unit = self.vehicle_id.odometer_unit
        self.purchaser_id = self.vehicle_id.driver_id

    @api.onchange('liter', 'price_per_liter', 'amount')
    def on_change_liter(self):
        """
        need to cast in float because the value received from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = self.liter
        price_per_liter = self.price_per_liter
        amount = self.amount
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)

    @api.onchange('price_per_liter')
    def on_change_price_per_liter(self):
        """
        need to cast in float because the value received from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = self.liter
        price_per_liter = self.price_per_liter
        amount = self.amount
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)

    @api.onchange('amount')
    def on_change_amount(self):
        """
        need to cast in float because the value received from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = self.liter
        price_per_liter = self.price_per_liter
        amount = self.amount
        if amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)
        elif liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)


class FleetVehicleLogServices(models.Model):

    _name = 'fleet.vehicle.log.services'
    _description = 'Services for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def _get_default_service_type(self):
        try:
            model_id = self.env.ref('fleet.type_service_service_8')
        except ValueError:
            model_id = False
        return model_id

    purchaser_id = fields.Many2one('res.partner', string='Purchaser',
                                   domain="['|', ('customer', '=', True), ('employee', '=', True)]")
    invoice_reference = fields.Char()
    vendor_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', True)]")
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    # we need to keep this field as a related with store=True because the graph view doesn't support (1) to address
    # fields from inherited table and (2) fields that aren't stored in database
    notes = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    date = fields.Date(default=fields.Date.context_today)

    _defaults = {
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'services'
    }

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.odometer_unit = self.vehicle_id.odometer_unit
        self.purchaser_id = self.vehicle_id.driver_id


class FleetServiceType(models.Model):

    _name = 'fleet.service.type'
    _description = 'Type of services available on a vehicle'

    name = fields.Char(required=True, translate=True)
    category = fields.Selection(selection=[('contract', 'Contract'), ('service', 'Service'), ('both', 'Both')],
                                required=True,
                                help='Choose whether the service refer to contracts, vehicle services or both')


class FleetVehicleLogContract(models.Model):

    _name = 'fleet.vehicle.log.contract'
    _description = 'Contract information on a vehicle'
    _order = 'state desc, expiration_date'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def _get_default_contract_type(self):
        try:
            model_id = self.env.ref('fleet.type_contract_leasing')
        except ValueError:
            model_id = False
        return model_id

    name = fields.Text(compute='_compute_vehicle_contract_name_get', store=True)
    start_date = fields.Date(string='Contract Start Date', help='Date when the coverage of the contract begins',
                             default=fields.Date.context_today)
    expiration_date = fields.Date(string='Contract Expiration Date',
                                  default=lambda self: self.compute_next_year_date(fields.Date.context_today(self)),
                                  help='Date when the coverage of the contract expirates '
                                       '(by default, one year after begin date)')
    days_left = fields.Integer(compute='compute_days_left', string='Warning Date')
    insurer_id = fields.Many2one('res.partner', string='Supplier')
    purchaser_id = fields.Many2one('res.partner', string='Contractor',
                                   help='Person to which the contract is signed for',
                                   default=lambda self: self.env['res.users'].browse(self._uid).partner_id.id or False)
    contract_reference = fields.Char(copy=False)
    state = fields.Selection(selection=[('open', 'In Progress'), ('toclose', 'To Close'), ('closed', 'Terminated')],
                             string='Status', readonly=True, help='Choose whether the contract is still valid or not',
                             copy=False, default='open')
    notes = fields.Text(string='Terms and Conditions',
                        help='Write here all supplementary information relative to this contract', copy=False)
    cost_generated = fields.Float(string='Recurring Cost Amount',
                                  help="Costs paid at regular intervals, depending on the cost frequency. "
                                       "If the cost frequency is set to unique, the cost will be logged at "
                                       "the start date")
    cost_frequency = fields.Selection(selection=[('no', 'No'), ('daily', 'Daily'), ('weekly', 'Weekly'),
                                                 ('monthly', 'Monthly'), ('yearly', 'Yearly')],
                                      string='Recurring Cost Frequency',
                                      help='Frequency of the recurring cost', required=True, default='no')
    generated_cost_ids = fields.One2many('fleet.vehicle.cost', 'contract_id', string='Generated Costs')
    sum_cost = fields.Float(compute='_compute_sum_cost', string='Indicative Costs Total')
    cost_id = fields.Many2one('fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    date = fields.Date(default=fields.Date.context_today)
    # we need to keep this field as a related with store=True because the graph view doesn't support (1) to
    # address fields from inherited table and (2) fields that aren't stored in database

    _defaults = {
        'cost_subtype_id': _get_default_contract_type,
        'cost_type': 'contract',
    }

    @api.one
    @api.depends('cost_subtype_id')
    def _compute_vehicle_contract_name_get(self):
        name = self.vehicle_id.name + ' / ' + self.cost_subtype_id.name
        self.name = self.date and name + ' / ' + self.date or name

    def compute_next_year_date(self, strdate):
        oneyear = relativedelta(years=+1)
        curdate = fields.Datetime.from_string(strdate)
        return fields.Datetime.to_string(curdate + oneyear)

    @api.multi
    def compute_days_left(self):
        """
        if contract is in an open state and is overdue, return 0
        if contract is in a closed state, return -1
        otherwise return the number of days before the contract expires
        """
        today = fields.Datetime.from_string(fields.Date.today())
        for log_contract in self:
            if log_contract.expiration_date and (log_contract.state in ('open', 'toclose')):
                renew_date = fields.Datetime.from_string(log_contract.expiration_date)
                diff_time = (renew_date - today).days
                log_contract.days_left = diff_time > 0 and diff_time or 0
            else:
                log_contract.days_left = -1

    @api.multi
    def _compute_sum_cost(self):
        for contract in self:
            contract.sum_cost = sum([cost.amount for cost in contract.cost_ids])

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.odometer_unit = self.vehicle_id.odometer_unit

    @api.one
    def contract_close(self):
        self.state = 'closed'

    @api.one
    def contract_open(self):
        self.state = 'open'

    @api.model
    def scheduler_manage_auto_costs(self):
        """
        This method is called by a cron task
        It creates costs for contracts having the "recurring cost" field setted, depending on their frequency
        For example, if a contract has a reccuring cost of 200 with a weekly frequency, this method creates a cost of
        200 on the first day of each week, from the date of the last recurring costs in the database to today
        If the contract has not yet any recurring costs in the database, the method generates the recurring costs
        from the start_date to today
        The created costs are associated to a contract thanks to the many2one field contract_id
        If the contract has no start_date, no cost will be created, even if the contract has recurring costs
        """
        VehicleCost = self.env['fleet.vehicle.cost']
        today = fields.Datetime.from_string(fields.Date.context_today(self))
        log_contract = self.env['fleet.vehicle.log.contract'].search([('state', '!=', 'closed'),
                                                                      '|', ('start_date', '=', None),
                                                                      ('cost_frequency', '!=', 'no')])
        deltas = {'yearly': relativedelta(years=+1), 'monthly': relativedelta(months=+1),
                  'weekly': relativedelta(weeks=+1), 'daily': relativedelta(days=+1)}
        for contract in log_contract:
            last_cost_date = contract.start_date
            if contract.generated_cost_ids:
                vehicle_cost = VehicleCost.search(['&', ('contract_id', '=', contract.id),
                                                 ('auto_generated', '=', True)], limit=1, order='date desc')[0]
                if vehicle_cost:
                    last_cost_date = vehicle_cost.date
            last_cost_date = fields.Datetime.from_string(last_cost_date)
            last_cost_date += deltas.get(contract.cost_frequency)
            while (last_cost_date <= today) and (
                    last_cost_date <= fields.Datetime.from_string(contract.expiration_date)):
                data = {
                    'amount': contract.cost_generated,
                    'date': fields.Date.to_string(last_cost_date),
                    'vehicle_id': contract.vehicle_id.id,
                    'cost_subtype_id': contract.cost_subtype_id.id,
                    'contract_id': contract.id,
                    'auto_generated': True
                }
                VehicleCost.create(data)
                last_cost_date += deltas.get(contract.cost_frequency)
        return True

    @api.model
    def scheduler_manage_contract_expiration(self):
        # This method is called by a cron task
        # It manages the state of a contract, possibly by posting a message on the vehicle concerned and
        # updating its status
        today = fields.Datetime.from_string(fields.Date.context_today(self))
        limit_date = fields.Date.to_string(today + relativedelta(days=+15))
        log_contract = self.search(['&', ('state', '=', 'open'), ('expiration_date', '<', limit_date)])
        result = defaultdict(int)
        for contract in log_contract:
            result[contract.vehicle_id.id] += 1

        for vehicle, value in result.items():
            self.env['fleet.vehicle'].browse(vehicle).message_post(body=_('%s contract(s) need(s) to be renewed '
                                                                          'and/or closed!') % (value))
        log_contract.write({'state': 'toclose'})

    @api.model
    def run_scheduler(self):
        self.scheduler_manage_auto_costs()
        self.scheduler_manage_contract_expiration()

    @api.multi
    def act_renew_contract(self):
        self.ensure_one()
        if len(self.ids) > 1:
            raise UserError(_("This operation should only be done for 1 single contract at a time, "
                            "as it it suppose to open a window as result"))
        # compute end date
        startdate = fields.Datetime.from_string(self.start_date)
        enddate = fields.Datetime.from_string(self.expiration_date)
        diffdate = (enddate - startdate)
        default = {
            'date': fields.Date.context_today(self),
            'start_date': fields.Datetime.to_string(fields.Datetime.from_string(self.expiration_date) +
                                                    datetime.timedelta(days=1)),
            'expiration_date': fields.Datetime.to_string(enddate + diffdate),
        }
        newid = self.copy(default).id
        return {
            'name': _("Renew Contract"),
            'view_mode': 'form',
            'view_id': self.env.ref('fleet.fleet_vehicle_log_contract_form').id,
            'view_type': 'tree,form',
            'res_model': 'fleet.vehicle.log.contract',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'domain': '[]',
            'res_id': newid,
            'context': {'active_id': newid},
        }
