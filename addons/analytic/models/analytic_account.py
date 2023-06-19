# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import itertools
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'plan_id, name asc'
    _check_company_auto = True
    _rec_names_search = ['name', 'code', 'partner_id']

    name = fields.Char(
        string='Analytic Account',
        index='trigram',
        required=True,
        tracking=True,
        translate=True,
    )
    code = fields.Char(
        string='Reference',
        index='btree',
        tracking=True,
    )
    active = fields.Boolean(
        'Active',
        help="Deactivate the account.",
        default=True,
        tracking=True,
    )

    plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Plan',
        check_company=True,
        required=True,
    )
    root_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Root Plan',
        check_company=True,
        compute="_compute_root_plan",
        store=True,
    )
    color = fields.Integer(
        'Color Index',
        related='plan_id.color',
    )

    line_ids = fields.One2many(
        'account.analytic.line',
        'account_id',
        string="Analytic Lines",
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # use auto_join to speed up name_search call
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        auto_join=True,
        tracking=True,
        check_company=True,
    )

    balance = fields.Monetary(
        compute='_compute_debit_credit_balance',
        string='Balance',
        groups='account.group_account_readonly',
    )
    debit = fields.Monetary(
        compute='_compute_debit_credit_balance',
        string='Debit',
        groups='account.group_account_readonly',
    )
    credit = fields.Monetary(
        compute='_compute_debit_credit_balance',
        string='Credit',
        groups='account.group_account_readonly',
    )

    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
    )

    @api.constrains('company_id')
    def _check_company_consistency(self):
        analytic_accounts = self.filtered('company_id')

        if not analytic_accounts:
            return

        self.flush_recordset(['company_id'])
        self.env['account.analytic.line'].flush_model(['account_id', 'company_id'])

        self._cr.execute('''
            SELECT line.account_id
            FROM account_analytic_line line
            JOIN account_analytic_account account ON line.account_id = account.id
            WHERE line.company_id != account.company_id and account.company_id IS NOT NULL
            AND account.id IN %s
        ''', [tuple(self.ids)])

        if self._cr.fetchone():
            raise UserError(_("You can't set a different company on your analytic account since there are some analytic items linked to it."))

    @api.depends('code', 'partner_id')
    def _compute_display_name(self):
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name = f'[{analytic.code}] {name}'
            if analytic.partner_id.commercial_partner_id.name:
                name = f'{name} - {analytic.partner_id.commercial_partner_id.name}'
            analytic.display_name = name

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault('name', _("%s (copy)", self.name))
        return super().copy_data(default)

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        """ Override _read_group to aggregate no-store compute: balance/debit/credit """
        SPECIAL = {'balance:sum', 'debit:sum', 'credit:sum'}
        if SPECIAL.isdisjoint(aggregates):
            return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

        base_aggregates = [*(agg for agg in aggregates if agg not in SPECIAL), 'id:recordset']
        base_result = super()._read_group(domain, groupby, base_aggregates, having, offset, limit, order)

        # base_result = [(a1, b1, records), (a2, b2, records), ...]
        result = []
        for *other, records in base_result:
            for index, spec in enumerate(itertools.chain(groupby, aggregates)):
                if spec in SPECIAL:
                    field_name = spec.split(':')[0]
                    other.insert(index, sum(records.mapped(field_name)))
            result.append(tuple(other))

        return result

    @api.depends('line_ids.amount')
    def _compute_debit_credit_balance(self):
        analytic_line_obj = self.env['account.analytic.line']
        domain = [
            ('account_id', 'in', self.ids),
            ('company_id', 'in', [False] + self.env.companies.ids)
        ]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        user_currency = self.env.company.currency_id
        credit_groups = analytic_line_obj._read_group(
            domain=domain + [('amount', '>=', 0.0)],
            groupby=['account_id', 'currency_id'],
            aggregates=['amount:sum'],
        )
        data_credit = defaultdict(float)
        for account, currency, amount_sum in credit_groups:
            data_credit[account.id] += currency._convert(
                amount_sum, user_currency, self.env.company, fields.Date.today())

        debit_groups = analytic_line_obj._read_group(
            domain=domain + [('amount', '<', 0.0)],
            groupby=['account_id', 'currency_id'],
            aggregates=['amount:sum'],
        )
        data_debit = defaultdict(float)
        for account, currency, amount_sum in debit_groups:
            data_debit[account.id] += currency._convert(
                amount_sum, user_currency, self.env.company, fields.Date.today())

        for account in self:
            account.debit = abs(data_debit.get(account.id, 0.0))
            account.credit = data_credit.get(account.id, 0.0)
            account.balance = account.credit - account.debit

    @api.depends('plan_id', 'plan_id.parent_path')
    def _compute_root_plan(self):
        for account in self:
            account.root_plan_id = int(account.plan_id.parent_path[:-1].split('/')[0]) if account.plan_id.parent_path else None
