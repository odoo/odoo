# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import itertools
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import groupby


class AccountAnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'plan_id, name asc'
    _check_company_auto = True
    _rec_names_search = ['name', 'code']

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
        required=True,
    )
    root_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Root Plan',
        related="plan_id.root_id",
        store=True,
    )
    color = fields.Integer(
        'Color Index',
        related='plan_id.color',
    )

    line_ids = fields.One2many(
        'account.analytic.line',
        'auto_account_id',  # magic link to the right column (plan) by using the context in the view
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
    )
    debit = fields.Monetary(
        compute='_compute_debit_credit_balance',
        string='Debit',
    )
    credit = fields.Monetary(
        compute='_compute_debit_credit_balance',
        string='Credit',
    )

    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
    )

    @api.constrains('company_id')
    def _check_company_consistency(self):
        for company, accounts in groupby(self, lambda account: account.company_id):
            if company and self.env['account.analytic.line'].sudo().search_count([
                ('auto_account_id', 'in', [account.id for account in accounts]),
                '!', ('company_id', 'child_of', company.id),
            ], limit=1):
                raise UserError(_("No company-switching allowed for your analytic account while there are some linked analytic items around! It's a recipe for an analytical disaster!"))

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
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for account, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", account.name)
        return vals_list

    def web_read(self, specification: dict[str, dict]) -> list[dict]:
        self_context = self
        if len(self) == 1:
            self_context = self.with_context(analytic_plan_id=self.plan_id.id)
        return super(AccountAnalyticAccount, self_context).web_read(specification)

    def _read_group_select(self, aggregate_spec, query):
        # flag balance/debit/credit as aggregatable, and manually sum the values
        # from the records in the group
        if aggregate_spec in ('balance:sum', 'debit:sum', 'credit:sum'):
            return super()._read_group_select('id:recordset', query)
        return super()._read_group_select(aggregate_spec, query)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        if aggregate_spec in ('balance:sum', 'debit:sum', 'credit:sum'):
            field_name = aggregate_spec.split(':')[0]
            column = super()._read_group_postprocess_aggregate('id:recordset', raw_values)
            return (sum(records.mapped(field_name)) for records in column)
        return super()._read_group_postprocess_aggregate(aggregate_spec, raw_values)

    @api.depends('line_ids.amount')
    def _compute_debit_credit_balance(self):
        def convert(amount, from_currency):
            return from_currency._convert(
                from_amount=amount,
                to_currency=self.env.company.currency_id,
                company=self.env.company,
                date=fields.Date.today(),
            )

        domain = [('company_id', 'in', [False] + self.env.companies.ids)]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        for plan, accounts in self.grouped('plan_id').items():
            credit_groups = self.env['account.analytic.line']._read_group(
                domain=domain + [(plan._column_name(), 'in', self.ids), ('amount', '>=', 0.0)],
                groupby=[plan._column_name(), 'currency_id'],
                aggregates=['amount:sum'],
            )
            data_credit = defaultdict(float)
            for account, currency, amount_sum in credit_groups:
                data_credit[account.id] += convert(amount_sum, currency)

            debit_groups = self.env['account.analytic.line']._read_group(
                domain=domain + [(plan._column_name(), 'in', self.ids), ('amount', '<', 0.0)],
                groupby=[plan._column_name(), 'currency_id'],
                aggregates=['amount:sum'],
            )
            data_debit = defaultdict(float)
            for account, currency, amount_sum in debit_groups:
                data_debit[account.id] += convert(amount_sum, currency)

            for account in accounts:
                account.debit = -data_debit.get(account.id, 0.0)
                account.credit = data_credit.get(account.id, 0.0)
                account.balance = account.credit - account.debit
