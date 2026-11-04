# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.tools.sql import SQL
from collections import defaultdict


class ContractHistory(models.Model):
    _name = 'hr.contract.history'
    _description = 'Contract history'
    _auto = False
    _order = 'is_under_contract'

    # Even though it would have been obvious to use the reference contract's id as the id of the
    # hr.contract.history model, it turned out it was a bad idea as this id could change (for instance if a
    # new contract is created with a later start date). The hr.contract.history is instead closely linked
    # to the employee. That's why we will use this id (employee_id) as the id of the hr.contract.history.
    contract_id = fields.Many2one('hr.contract', readonly=True)

    name = fields.Char('Contract Name', readonly=True)
    date_hired = fields.Date('Hire Date', readonly=True)
    date_start = fields.Date('Start Date', readonly=True)
    date_end = fields.Date('End Date', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    active_employee = fields.Boolean('Active Employee', readonly=True)
    is_under_contract = fields.Boolean('Is Currently Under Contract', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string='Salary Structure Type', readonly=True)
    hr_responsible_id = fields.Many2one('res.users', string='HR Responsible', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Position', readonly=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('open', 'Running'),
        ('close', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True)
    resource_calendar_id = fields.Many2one('resource.calendar', string="Working Schedule", readonly=True)
    wage = fields.Monetary('Wage', help="Employee's monthly gross wage.", readonly=True, aggregator="avg")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    company_country_id = fields.Many2one('res.country', string="Company country", related='company_id.country_id', readonly=True)
    country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True)
    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True)
    contract_type_id = fields.Many2one('hr.contract.type', 'Contract Type', readonly=True)
    contract_ids = fields.One2many('hr.contract', string='Contracts', compute='_compute_contract_ids', readonly=True, compute_sudo=True)
    contract_count = fields.Integer(compute='_compute_contract_count', string="# Contracts")
    under_contract_state = fields.Selection([
        ('done', 'Under Contract'),
        ('blocked', 'Not Under Contract')
    ], string='Contractual Status', compute='_compute_under_contract_state')
    activity_state = fields.Selection(related='contract_id.activity_state')

    @api.depends('contract_ids')
    def _compute_contract_count(self):
        for history in self:
            history.contract_count = len(history.contract_ids)

    @api.depends('is_under_contract')
    def _compute_under_contract_state(self):
        for history in self:
            history.under_contract_state = 'done' if history.is_under_contract else 'blocked'

    @api.depends('employee_id.name')
    def _compute_display_name(self):
        for history in self:
            history.display_name = _("%s's Contracts History", history.employee_id.name)

    @api.model
    def _get_fields(self):
        return ','.join('contract.%s' % name for name, field in self._fields.items()
                        if field.store 
                        and field.type not in ['many2many', 'one2many', 'related']
                        and field.name not in ['id', 'contract_id', 'employee_id', 'date_hired', 'is_under_contract', 'active_employee'])

    def _read_group_groupby(self, groupby_spec, query):
        if groupby_spec != 'activity_state':
            return super()._read_group_groupby(groupby_spec, query)

        Contract = self.env['hr.contract']
        # we use Contract._table as the JOIN alias, because that's the one used
        # by the call to Contract._read_group_groupby() below
        query.add_join('LEFT JOIN', Contract._table, Contract._table, SQL(
            "%s = %s",
            self._field_to_sql(self._table, 'contract_id', query),
            SQL.identifier(Contract._table, 'id'),
        ))
        activity_state_sql = Contract._read_group_groupby(groupby_spec, query)
        # Change the kind of JOIN -> JOIN LEFT because
        # LEFT JOIN follow by JOIN doesn't have the same semantic
        __, table, condition = query._joins['hr_contract__last_activity_state']
        query._joins['hr_contract__last_activity_state'] = (SQL('LEFT JOIN'), table, condition)
        return activity_state_sql

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Reference contract is the one with the latest start_date.
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
            WITH contract_information AS (
                SELECT DISTINCT employee_id,
                                company_id,
                                FIRST_VALUE(id) OVER w_partition AS id,
                                MAX(CASE
                                    WHEN state='open' THEN 1
                                    WHEN state='draft' AND kanban_state='done' THEN 1
                                    ELSE 0 END) OVER w_partition AS is_under_contract
                FROM   hr_contract AS contract
                WHERE  contract.active = true
                WINDOW w_partition AS (
                    PARTITION BY contract.employee_id, contract.company_id
                    ORDER BY
                        CASE
                            WHEN contract.state = 'open' THEN 0
                            WHEN contract.state = 'draft' THEN 1
                            WHEN contract.state = 'close' THEN 2
                            WHEN contract.state = 'cancel' THEN 3
                            ELSE 4 END,
                        contract.date_start DESC
                    RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                )
            )
            SELECT DISTINCT employee.id AS id,
                            employee.id AS employee_id,
                            employee.active AS active_employee,
                            contract.id AS contract_id,
                            contract_information.is_under_contract::bool AS is_under_contract,
                            employee.first_contract_date AS date_hired,
                            %s
            FROM       hr_contract AS contract
            INNER JOIN contract_information ON contract.id = contract_information.id
            RIGHT JOIN hr_employee AS employee
                ON  contract_information.employee_id = employee.id
                AND contract.company_id = employee.company_id
            WHERE   employee.employee_type IN ('employee', 'student', 'trainee')
        )""" % (self._table, self._get_fields()))

    @api.depends('employee_id.contract_ids')
    def _compute_contract_ids(self):
        sorted_contracts = self.mapped('employee_id.contract_ids').sorted('date_start', reverse=True)

        mapped_employee_contracts = defaultdict(lambda: self.env['hr.contract'])
        for contract in sorted_contracts:
            mapped_employee_contracts[contract.employee_id] |= contract

        for history in self:
            history.contract_ids = mapped_employee_contracts[history.employee_id]

    def hr_contract_view_form_new_action(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('hr_contract.action_hr_contract')
        action.update({
            'context': {'default_employee_id': self.employee_id.id},
            'view_mode': 'form',
            'view_id': self.env.ref('hr_contract.hr_contract_view_form').id,
            'views': [(self.env.ref('hr_contract.hr_contract_view_form').id, 'form')],
        })
        return action
