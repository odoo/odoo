# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
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

    def name_get(self):
        res = []
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name = f'[{analytic.code}] {name}'
            if analytic.partner_id.commercial_partner_id.name:
                name = f'{name} - {analytic.partner_id.commercial_partner_id.name}'
            res.append((analytic.id, name))
        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault('name', _("%s (copy)", self.name))
        return super().copy_data(default)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
            Override read_group to calculate the sum of the non-stored fields that depend on the user context
        """
        res = super(AccountAnalyticAccount, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        accounts = self.env['account.analytic.account']
        for line in res:
            if '__domain' in line:
                accounts = self.search(line['__domain'])
            if 'balance' in fields:
                line['balance'] = sum(accounts.mapped('balance'))
            if 'debit' in fields:
                line['debit'] = sum(accounts.mapped('debit'))
            if 'credit' in fields:
                line['credit'] = sum(accounts.mapped('credit'))
        return res

    @api.depends('line_ids.amount')
    def _compute_debit_credit_balance(self):
        Curr = self.env['res.currency']
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
        credit_groups = analytic_line_obj.read_group(
            domain=domain + [('amount', '>=', 0.0)],
            fields=['account_id', 'currency_id', 'amount'],
            groupby=['account_id', 'currency_id'],
            lazy=False,
        )
        data_credit = defaultdict(float)
        for l in credit_groups:
            data_credit[l['account_id'][0]] += Curr.browse(l['currency_id'][0])._convert(
                l['amount'], user_currency, self.env.company, fields.Date.today())

        debit_groups = analytic_line_obj.read_group(
            domain=domain + [('amount', '<', 0.0)],
            fields=['account_id', 'currency_id', 'amount'],
            groupby=['account_id', 'currency_id'],
            lazy=False,
        )
        data_debit = defaultdict(float)
        for l in debit_groups:
            data_debit[l['account_id'][0]] += Curr.browse(l['currency_id'][0])._convert(
                l['amount'], user_currency, self.env.company, fields.Date.today())

        for account in self:
            account.debit = abs(data_debit.get(account.id, 0.0))
            account.credit = data_credit.get(account.id, 0.0)
            account.balance = account.credit - account.debit

    @api.depends('plan_id', 'plan_id.parent_path')
    def _compute_root_plan(self):
        for account in self:
            account.root_plan_id = int(account.plan_id.parent_path[:-1].split('/')[0]) if account.plan_id.parent_path else None
