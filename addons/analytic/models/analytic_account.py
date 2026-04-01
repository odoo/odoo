# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import itertools
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import groupby, SQL


class AccountAnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'plan_id, name asc'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
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
        index=True,
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

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        # use bypass_access to speed up name_search call
        bypass_search_access=True,
        tracking=True,
        check_company=True,
        index='btree_not_null',
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
                raise UserError(_("You can't change the company of an analytic account that already has analytic items! It's a recipe for an analytical disaster!"))

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
        if aggregate_spec in (
            'balance:sum',
            'balance:sum_currency',
            'debit:sum',
            'debit:sum_currency',
            'credit:sum',
            'credit:sum_currency',
        ):
            return super()._read_group_select('id:recordset', query)
        return super()._read_group_select(aggregate_spec, query)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        if aggregate_spec in (
            'balance:sum',
            'balance:sum_currency',
            'debit:sum',
            'debit:sum_currency',
            'credit:sum',
            'credit:sum_currency',
        ):
            field_name, op = aggregate_spec.split(':')
            column = super()._read_group_postprocess_aggregate('id:recordset', raw_values)
            if op == 'sum':
                return (sum(records.mapped(field_name)) for records in column)
            if op == 'sum_currency':
                return (sum(record.currency_id._convert(
                    from_amount=record[field_name],
                    to_currency=self.env.company.currency_id,
                ) for record in records) for records in column)
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
        if self.env.context.get('from_date', False):
            domain.append(('date', '>=', self.env.context['from_date']))
        if self.env.context.get('to_date', False):
            domain.append(('date', '<=', self.env.context['to_date']))

        for plan, accounts in self.grouped('plan_id').items():
            if not plan:
                accounts.debit = accounts.credit = accounts.balance = 0
                continue
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

    def _update_accounts_in_analytic_lines(self, new_fname, current_fname, accounts):
        if current_fname != new_fname:
            domain = [
                (new_fname, 'not in', accounts.ids + [False]),
                (current_fname, 'in', accounts.ids),
            ]
            if self.env['account.analytic.line'].sudo().search_count(domain, limit=1):
                list_view = self.env.ref('analytic.view_account_analytic_line_tree', raise_if_not_found=False)
                raise RedirectWarning(
                    message=_("Whoa there! Making this change would wipe out your current data. Let's avoid that, shall we?"),
                    action={
                        'res_model': 'account.analytic.line',
                        'type': 'ir.actions.act_window',
                        'domain': domain,
                        'target': 'new',
                        'views': [(list_view and list_view.id, 'list')]
                    },
                    button_text=_("See them"),
                )
            self.env.cr.execute(SQL(
                """
                UPDATE account_analytic_line
                   SET %(new_fname)s = %(current_fname)s,
                       %(current_fname)s = NULL
                 WHERE %(current_fname)s = ANY(%(account_ids)s)
                """,
                new_fname=SQL.identifier(new_fname),
                current_fname=SQL.identifier(current_fname),
                account_ids=accounts.ids,
            ))
            self.env['account.analytic.line'].invalidate_model()

    def write(self, vals):
        if vals.get('plan_id'):
            new_fname = self.env['account.analytic.plan'].browse(vals['plan_id'])._column_name()
            for plan, accounts in self.grouped('plan_id').items():
                current_fname = plan._column_name()
                self._update_accounts_in_analytic_lines(new_fname, current_fname, accounts)
        return super().write(vals)
