# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class FleetVehicleLogContract(models.Model):

    _name = 'fleet.vehicle.log.contract'
    _description = 'Contract information on a vehicle'
    _order = 'state desc, expiration_date'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def default_get(self, fields):
        res = super(FleetVehicleLogContract, self).default_get(fields)
        try:
            service_type_id = self.env.ref('fleet.type_contract_leasing').id
        except ValueError:
            service_type_id = False
        res.update({'cost_type': 'contract', 'cost_subtype_id': service_type_id})
        return res

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
