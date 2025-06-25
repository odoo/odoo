# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class FleetVehicleLogContract(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'fleet.vehicle.log.contract'
    _description = 'Vehicle Contract'
    _order = 'state desc,expiration_date'

    def compute_next_year_date(self, strdate):
        oneyear = relativedelta(years=1)
        start_date = fields.Date.from_string(strdate)
        return fields.Date.to_string(start_date + oneyear)

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True, check_company=True, tracking=True)
    cost_subtype_id = fields.Many2one('fleet.service.type', 'Type', help='Cost type purchased with this cost', domain=[('category', '=', 'contract')])
    amount = fields.Monetary('Cost', tracking=True)
    date = fields.Date(help='Date when the cost has been executed')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    name = fields.Char(string='Name', compute='_compute_contract_name', store=True, readonly=False)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env['fleet.vehicle'].browse(self._context.get('active_id')).manager_id,
        index=True)
    start_date = fields.Date(
        'Contract Start Date', default=fields.Date.context_today, tracking=True,
        help='Date when the coverage of the contract begins')
    expiration_date = fields.Date(
        'Contract Expiration Date', default=lambda self:
        self.compute_next_year_date(fields.Date.context_today(self)),
        tracking=True,
        help='Date when the coverage of the contract expirates (by default, one year after begin date)')
    days_left = fields.Integer(compute='_compute_days_left', string='Warning Date')
    expires_today = fields.Boolean(compute='_compute_days_left')
    has_open_contract = fields.Boolean(compute='_compute_has_open_contract')
    insurer_id = fields.Many2one('res.partner', 'Vendor')
    purchaser_id = fields.Many2one(related='vehicle_id.driver_id', string='Driver')
    ins_ref = fields.Char('Reference', size=64, copy=False)
    state = fields.Selection(
        [('futur', 'New'),
         ('open', 'Running'),
         ('expired', 'Expired'),
         ('closed', 'Cancelled')
        ], 'Status', default='open',
        help='Choose whether the contract is still valid or not',
        tracking=True,
        copy=False)
    notes = fields.Html('Terms and Conditions', copy=False)
    cost_generated = fields.Monetary('Recurring Cost', tracking=True)
    cost_frequency = fields.Selection([
        ('no', 'No'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
        ], 'Recurring Cost Frequency', default='monthly', required=True, tracking=True)
    service_ids = fields.Many2many('fleet.service.type', string="Included Services")

    @api.depends('vehicle_id.name', 'cost_subtype_id')
    def _compute_contract_name(self):
        for record in self:
            name = record.vehicle_id.name
            if name and record.cost_subtype_id.name:
                name = record.cost_subtype_id.name + ' ' + name
            record.name = name

    @api.depends('vehicle_id')
    def _compute_has_open_contract(self):
        today = fields.Date.today()
        open_contracts = self.env['fleet.vehicle.log.contract'].search([
            ('vehicle_id', 'in', self.vehicle_id.ids),
            ('state', '=', 'open'),
            ('expiration_date', '>=', today)
        ])
        for log_contract in self:
            log_contract.has_open_contract = log_contract.vehicle_id in open_contracts.vehicle_id

    @api.depends('expiration_date', 'state')
    def _compute_days_left(self):
        """return a dict with as value for each contract an integer
        if contract is in an open state and is overdue, return 0
        if contract is in a closed state, return -1
        otherwise return the number of days before the contract expires
        """
        today = fields.Date.from_string(fields.Date.today())
        for record in self:
            if record.expiration_date and record.state in ['open', 'expired']:
                renew_date = fields.Date.from_string(record.expiration_date)
                diff_time = (renew_date - today).days
                record.days_left = diff_time if diff_time > 0 else 0
                record.expires_today = diff_time == 0
            else:
                record.days_left = -1
                record.expires_today = False

    def write(self, vals):
        res = super(FleetVehicleLogContract, self).write(vals)
        if 'start_date' in vals or 'expiration_date' in vals:
            date_today = fields.Date.today()
            future_contracts, running_contracts, expired_contracts = self.env[self._name], self.env[self._name], self.env[self._name]
            for contract in self.filtered(lambda c: c.start_date and c.state != 'closed'):
                if date_today < contract.start_date:
                    future_contracts |= contract
                elif not contract.expiration_date or contract.start_date <= date_today <= contract.expiration_date:
                    running_contracts |= contract
                else:
                    expired_contracts |= contract
            future_contracts.action_draft()
            running_contracts.action_open()
            expired_contracts.action_expire()
        if vals.get('expiration_date') or vals.get('user_id'):
            self.activity_reschedule(['fleet.mail_act_fleet_contract_to_renew'], date_deadline=vals.get('expiration_date'), new_user_id=vals.get('user_id'))
        return res

    def action_close(self):
        self.write({'state': 'closed'})

    def action_draft(self):
        self.write({'state': 'futur'})

    def action_open(self):
        self.write({'state': 'open'})

    def action_expire(self):
        self.write({'state': 'expired'})

    @api.model
    def scheduler_manage_contract_expiration(self):
        # This method is called by a cron task
        # It manages the state of a contract, possibly by posting a message on the vehicle concerned and updating its status
        params = self.env['ir.config_parameter'].sudo()
        delay_alert_contract = int(params.get_param('hr_fleet.delay_alert_contract', default=30))
        date_today = fields.Date.from_string(fields.Date.today())
        outdated_days = fields.Date.to_string(date_today + relativedelta(days=+delay_alert_contract))
        reminder_activity_type = self.env.ref('fleet.mail_act_fleet_contract_to_renew', raise_if_not_found=False) or self.env['mail.activity.type']
        nearly_expired_contracts = self.search([
            ('state', '=', 'open'),
            ('expiration_date', '<', outdated_days),
            ('user_id', '!=', False)
        ]
        ).filtered(
            lambda nec: reminder_activity_type not in nec.activity_ids.activity_type_id
        )

        for contract in nearly_expired_contracts:
            contract.activity_schedule(
                'fleet.mail_act_fleet_contract_to_renew', contract.expiration_date,
                user_id=contract.user_id.id)

        expired_contracts = self.search([('state', 'not in', ['expired', 'closed']), ('expiration_date', '<',fields.Date.today() )])
        expired_contracts.action_expire()

        futur_contracts = self.search([('state', 'not in', ['futur', 'closed']), ('start_date', '>', fields.Date.today())])
        futur_contracts.action_draft()

        now_running_contracts = self.search([('state', '=', 'futur'), ('start_date', '<=', fields.Date.today())])
        now_running_contracts.action_open()

    def run_scheduler(self):
        self.scheduler_manage_contract_expiration()
