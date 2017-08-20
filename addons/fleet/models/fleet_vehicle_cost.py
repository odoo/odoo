# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from dateutil.relativedelta import relativedelta


class FleetVehicleCost(models.Model):
    _name = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle'
    _order = 'date desc, vehicle_id asc'

    name = fields.Char(related='vehicle_id.name', string='Name', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True, help='Vehicle concerned by this log')
    cost_subtype_id = fields.Many2one('fleet.service.type', 'Type', help='Cost type purchased with this cost')
    amount = fields.Float('Total Price')
    cost_type = fields.Selection([
        ('contract', 'Contract'),
        ('services', 'Services'),
        ('fuel', 'Fuel'),
        ('other', 'Other')
        ], 'Category of the cost', default="other", help='For internal purpose only', required=True)
    parent_id = fields.Many2one('fleet.vehicle.cost', 'Parent', help='Parent cost to this current cost')
    cost_ids = fields.One2many('fleet.vehicle.cost', 'parent_id', 'Included Services', copy=True)
    odometer_id = fields.Many2one('fleet.vehicle.odometer', 'Odometer', help='Odometer measure of the vehicle at the moment of this log')
    odometer = fields.Float(compute="_get_odometer", inverse='_set_odometer', string='Odometer Value',
        help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    date = fields.Date(help='Date when the cost has been executed')
    contract_id = fields.Many2one('fleet.vehicle.log.contract', 'Contract', help='Contract attached to this cost')
    auto_generated = fields.Boolean('Automatically Generated', readonly=True)
    description = fields.Char("Cost Description")

    def _get_odometer(self):
        for record in self:
            if record.odometer_id:
                record.odometer = record.odometer_id.value

    def _set_odometer(self):
        for record in self:
            if not record.odometer:
                raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
            odometer = self.env['fleet.vehicle.odometer'].create({
                'value': record.odometer,
                'date': record.date or fields.Date.context_today(record),
                'vehicle_id': record.vehicle_id.id
            })
            self.odometer_id = odometer

    @api.model
    def create(self, data):
        # make sure that the data are consistent with values of parent and contract records given
        if 'parent_id' in data and data['parent_id']:
            parent = self.browse(data['parent_id'])
            data['vehicle_id'] = parent.vehicle_id.id
            data['date'] = parent.date
            data['cost_type'] = parent.cost_type
        if 'contract_id' in data and data['contract_id']:
            contract = self.env['fleet.vehicle.log.contract'].browse(data['contract_id'])
            data['vehicle_id'] = contract.vehicle_id.id
            data['cost_subtype_id'] = contract.cost_subtype_id.id
            data['cost_type'] = contract.cost_type
        if 'odometer' in data and not data['odometer']:
            # if received value for odometer is 0, then remove it from the data as it would result to the creation of a
            # odometer log with 0, which is to be avoided
            del(data['odometer'])
        return super(FleetVehicleCost, self).create(data)


class FleetVehicleLogContract(models.Model):

    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _name = 'fleet.vehicle.log.contract'
    _description = 'Contract information on a vehicle'
    _order = 'state desc,expiration_date'

    def compute_next_year_date(self, strdate):
        oneyear = relativedelta(years=1)
        start_date = fields.Date.from_string(strdate)
        return fields.Date.to_string(start_date + oneyear)

    @api.model
    def default_get(self, default_fields):
        res = super(FleetVehicleLogContract, self).default_get(default_fields)
        contract = self.env.ref('fleet.type_contract_leasing', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': contract and contract.id or False,
            'cost_type': 'contract'
        })
        return res

    name = fields.Text(compute='_compute_contract_name', store=True)
    active = fields.Boolean(default=True)
    start_date = fields.Date('Contract Start Date', default=fields.Date.context_today, help='Date when the coverage of the contract begins')
    expiration_date = fields.Date('Contract Expiration Date', default=lambda self: self.compute_next_year_date(fields.Date.context_today(self)),
        help='Date when the coverage of the contract expirates (by default, one year after begin date)')
    days_left = fields.Integer(compute='_compute_days_left', string='Warning Date')
    insurer_id = fields.Many2one('res.partner', 'Vendor')
    purchaser_id = fields.Many2one('res.partner', 'Contractor', default=lambda self: self.env.user.partner_id.id,
        help='Person to which the contract is signed for')
    ins_ref = fields.Char('Contract Reference', size=64, copy=False)
    state = fields.Selection([
        ('open', 'In Progress'),
        ('toclose', 'To Close'),
        ('closed', 'Terminated')
        ], 'Status', default='open', readonly=True, help='Choose wheter the contract is still valid or not',
                              copy=False)
    notes = fields.Text('Terms and Conditions', help='Write here all supplementary information relative to this contract', copy=False)
    cost_generated = fields.Float('Recurring Cost Amount',
        help="Costs paid at regular intervals, depending on the cost frequency."
             "If the cost frequency is set to unique, the cost will be logged at the start date")
    cost_frequency = fields.Selection([
        ('no', 'No'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
        ], 'Recurring Cost Frequency', default='no', help='Frequency of the recuring cost', required=True)
    generated_cost_ids = fields.One2many('fleet.vehicle.cost', 'contract_id', 'Generated Costs')
    sum_cost = fields.Float(compute='_compute_sum_cost', string='Indicative Costs Total')
    cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')
    # we need to keep this field as a related with store=True because the graph view doesn't support
    # (1) to address fields from inherited table
    # (2) fields that aren't stored in database
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    odometer = fields.Float(string='Odometer at creation', help='Odometer measure of the vehicle at the moment of the contract creation')

    @api.depends('vehicle_id', 'cost_subtype_id', 'date')
    def _compute_contract_name(self):
        for record in self:
            name = record.vehicle_id.name
            if record.cost_subtype_id.name:
                name += ' / ' + record.cost_subtype_id.name
            if record.date:
                name += ' / ' + record.date
            record.name = name

    @api.depends('expiration_date', 'state')
    def _compute_days_left(self):
        """return a dict with as value for each contract an integer
        if contract is in an open state and is overdue, return 0
        if contract is in a closed state, return -1
        otherwise return the number of days before the contract expires
        """
        for record in self:
            if (record.expiration_date and (record.state == 'open' or record.state == 'toclose')):
                today = fields.Date.from_string(fields.Date.today())
                renew_date = fields.Date.from_string(record.expiration_date)
                diff_time = (renew_date - today).days
                record.days_left = diff_time > 0 and diff_time or 0
            else:
                record.days_left = -1

    @api.depends('cost_ids.amount')
    def _compute_sum_cost(self):
        for contract in self:
            contract.sum_cost = sum(contract.cost_ids.mapped('amount'))

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.odometer_unit = self.vehicle_id.odometer_unit

    @api.multi
    def contract_close(self):
        for record in self:
            record.state = 'closed'

    @api.multi
    def contract_open(self):
        for record in self:
            record.state = 'open'

    @api.multi
    def act_renew_contract(self):
        assert len(self.ids) == 1, "This operation should only be done for 1 single contract at a time, as it it suppose to open a window as result"
        for element in self:
            # compute end date
            startdate = fields.Date.from_string(element.start_date)
            enddate = fields.Date.from_string(element.expiration_date)
            diffdate = (enddate - startdate)
            default = {
                'date': fields.Date.context_today(self),
                'start_date': fields.Date.to_string(fields.Date.from_string(element.expiration_date) + relativedelta(days=1)),
                'expiration_date': fields.Date.to_string(enddate + diffdate),
            }
            newid = element.copy(default).id
        return {
            'name': _("Renew Contract"),
            'view_mode': 'form',
            'view_id': self.env.ref('fleet.fleet_vehicle_log_contract_view_form').id,
            'view_type': 'tree,form',
            'res_model': 'fleet.vehicle.log.contract',
            'type': 'ir.actions.act_window',
            'domain': '[]',
            'res_id': newid,
            'context': {'active_id': newid},
        }

    @api.model
    def scheduler_manage_auto_costs(self):
        # This method is called by a cron task
        # It creates costs for contracts having the "recurring cost" field setted, depending on their frequency
        # For example, if a contract has a reccuring cost of 200 with a weekly frequency, this method creates a cost of 200 on the
        # first day of each week, from the date of the last recurring costs in the database to today
        # If the contract has not yet any recurring costs in the database, the method generates the recurring costs from the start_date to today
        # The created costs are associated to a contract thanks to the many2one field contract_id
        # If the contract has no start_date, no cost will be created, even if the contract has recurring costs
        VehicleCost = self.env['fleet.vehicle.cost']
        deltas = {
            'yearly': relativedelta(years=+1),
            'monthly': relativedelta(months=+1),
            'weekly': relativedelta(weeks=+1),
            'daily': relativedelta(days=+1)
        }
        contracts = self.env['fleet.vehicle.log.contract'].search([('state', '!=', 'closed')], offset=0, limit=None, order=None)
        for contract in contracts:
            if not contract.start_date or contract.cost_frequency == 'no':
                continue
            found = False
            last_cost_date = contract.start_date
            if contract.generated_cost_ids:
                last_autogenerated_cost = VehicleCost.search([
                    ('contract_id', '=', contract.id),
                    ('auto_generated', '=', True)
                ], offset=0, limit=1, order='date desc')
                if last_autogenerated_cost:
                    found = True
                    last_cost_date = last_autogenerated_cost.date
            startdate = fields.Date.from_string(last_cost_date)
            if found:
                startdate += deltas.get(contract.cost_frequency)
            today = fields.Date.from_string(fields.Date.context_today(self))
            while (startdate <= today) & (startdate <= fields.Date.from_string(contract.expiration_date)):
                data = {
                    'amount': contract.cost_generated,
                    'date': fields.Date.context_today(self),
                    'vehicle_id': contract.vehicle_id.id,
                    'cost_subtype_id': contract.cost_subtype_id.id,
                    'contract_id': contract.id,
                    'auto_generated': True
                }
                self.env['fleet.vehicle.cost'].create(data)
                startdate += deltas.get(contract.cost_frequency)
        return True

    @api.model
    def scheduler_manage_contract_expiration(self):
        # This method is called by a cron task
        # It manages the state of a contract, possibly by posting a message on the vehicle concerned and updating its status
        date_today = fields.Date.from_string(fields.Date.context_today(self))
        limit_date = fields.Date.to_string(date_today + relativedelta(days=+15))
        contracts = self.search([('state', '=', 'open'), ('expiration_date', '<', limit_date)])
        res = {}
        for contract in contracts:
            if contract.vehicle_id.id in res:
                res[contract.vehicle_id.id] += 1
            else:
                res[contract.vehicle_id.id] = 1

        Vehicle = self.env['fleet.vehicle']
        for vehicle, value in res.items():
            Vehicle.browse(vehicle).message_post(body=_('%s contract(s) need(s) to be renewed and/or closed!') % value)
        return contracts.write({'state': 'toclose'})

    @api.model
    def run_scheduler(self):
        self.scheduler_manage_auto_costs()
        self.scheduler_manage_contract_expiration()


class FleetVehicleLogFuel(models.Model):
    _name = 'fleet.vehicle.log.fuel'
    _description = 'Fuel log for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def default_get(self, default_fields):
        res = super(FleetVehicleLogFuel, self).default_get(default_fields)
        service = self.env.ref('fleet.type_service_refueling', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': service and service.id or False,
            'cost_type': 'fuel'
        })
        return res

    liter = fields.Float()
    price_per_liter = fields.Float()
    purchaser_id = fields.Many2one('res.partner', 'Purchaser', domain="['|',('customer','=',True),('employee','=',True)]")
    inv_ref = fields.Char('Invoice Reference', size=64)
    vendor_id = fields.Many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]")
    notes = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')
    # we need to keep this field as a related with store=True because the graph view doesn't support
    # (1) to address fields from inherited table
    # (2) fields that aren't stored in database
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.odometer_unit = self.vehicle_id.odometer_unit
            self.purchaser_id = self.vehicle_id.driver_id.id

    @api.onchange('liter', 'price_per_liter', 'amount')
    def _onchange_liter_price_amount(self):
        # need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        # make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        # liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        # of 3.0/2=1.5)
        # If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        # onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        # computation to 2 decimal
        liter = float(self.liter)
        price_per_liter = float(self.price_per_liter)
        amount = float(self.amount)
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)


class FleetVehicleLogServices(models.Model):
    _name = 'fleet.vehicle.log.services'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _description = 'Services for vehicles'

    @api.model
    def default_get(self, default_fields):
        res = super(FleetVehicleLogServices, self).default_get(default_fields)
        service = self.env.ref('fleet.type_service_service_8', raise_if_not_found=False)
        res.update({
            'date': fields.Date.context_today(self),
            'cost_subtype_id': service and service.id or False,
            'cost_type': 'services'
        })
        return res

    purchaser_id = fields.Many2one('res.partner', 'Purchaser', domain="['|',('customer','=',True),('employee','=',True)]")
    inv_ref = fields.Char('Invoice Reference')
    vendor_id = fields.Many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]")
    # we need to keep this field as a related with store=True because the graph view doesn't support
    # (1) to address fields from inherited table and (2) fields that aren't stored in database
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    notes = fields.Text()
    cost_id = fields.Many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade')

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.odometer_unit = self.vehicle_id.odometer_unit
            self.purchaser_id = self.vehicle_id.driver_id.id
