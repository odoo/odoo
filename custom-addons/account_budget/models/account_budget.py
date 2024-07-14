# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta
import itertools

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv.expression import AND

# ---------------------------------------------------------
# Budgets
# ---------------------------------------------------------
class AccountBudgetPost(models.Model):
    _name = "account.budget.post"
    _order = "name"
    _description = "Budgetary Position"

    name = fields.Char('Name', required=True)
    account_ids = fields.Many2many('account.account', 'account_budget_rel', 'budget_id', 'account_id', 'Accounts',
        check_company=True,
        domain="[('deprecated', '=', False)]")
    company_id = fields.Many2one('res.company', 'Company', required=True,
        default=lambda self: self.env.company)

    @api.constrains('account_ids')
    def _check_account_ids(self):
        for budget in self:
            if not budget.account_ids:
                raise ValidationError(_('The budget must have at least one account.'))


class CrossoveredBudget(models.Model):
    _name = "crossovered.budget"
    _description = "Budget"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Budget Name', required=True)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'crossovered_budget_id', 'Budget Lines', copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
        default=lambda self: self.env.company)

    def action_budget_confirm(self):
        self.write({'state': 'confirm'})

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_budget_validate(self):
        self.write({'state': 'validate'})

    def action_budget_cancel(self):
        self.write({'state': 'cancel'})

    def action_budget_done(self):
        self.write({'state': 'done'})


class CrossoveredBudgetLines(models.Model):
    _name = "crossovered.budget.lines"
    _description = "Budget Line"

    name = fields.Char(compute='_compute_line_name')
    crossovered_budget_id = fields.Many2one('crossovered.budget', 'Budget', ondelete='cascade', index=True, required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    analytic_plan_id = fields.Many2one('account.analytic.plan', 'Analytic Plan', related='analytic_account_id.plan_id', readonly=True)
    general_budget_id = fields.Many2one('account.budget.post', 'Budgetary Position')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    paid_date = fields.Date('Paid Date')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    planned_amount = fields.Monetary(
        'Planned Amount', required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    practical_amount = fields.Monetary(
        compute='_compute_practical_amount', string='Practical Amount', help="Amount really earned/spent.")
    theoritical_amount = fields.Monetary(
        compute='_compute_theoritical_amount', string='Theoretical Amount',
        help="Amount you are supposed to have earned/spent at this date.")
    percentage = fields.Float(
        compute='_compute_percentage', string='Achievement', group_operator='avg',
        help="Comparison between practical and theoretical amount. This measure tells you if you are below or over budget.")
    company_id = fields.Many2one(related='crossovered_budget_id.company_id', comodel_name='res.company',
        string='Company', store=True, readonly=True)
    is_above_budget = fields.Boolean(compute='_is_above_budget')
    crossovered_budget_state = fields.Selection(related='crossovered_budget_id.state', string='Budget State', store=True, readonly=True)

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        SPECIAL = {'practical_amount:sum', 'theoritical_amount:sum', 'percentage:avg'}
        if SPECIAL.isdisjoint(aggregates):
            return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

        base_aggregates = [*(agg for agg in aggregates if agg not in SPECIAL), 'id:recordset']
        base_result = super()._read_group(domain, groupby, base_aggregates, having, offset, limit, order)

        # base_result = [(a1, b1, records), (a2, b2, records), ...]
        result = []
        for *other, records in base_result:
            for index, spec in enumerate(itertools.chain(groupby, aggregates)):
                if spec in SPECIAL:
                    field_name, op = spec.split(':')
                    res = sum(records.mapped(field_name))
                    if op == 'avg' and records:
                        res /= len(records)
                    other.insert(index, res)
            result.append(tuple(other))

        return result

    def _is_above_budget(self):
        for line in self:
            if line.theoritical_amount >= 0:
                line.is_above_budget = line.practical_amount > line.theoritical_amount
            else:
                line.is_above_budget = line.practical_amount < line.theoritical_amount

    @api.depends("crossovered_budget_id", "general_budget_id", "analytic_account_id")
    def _compute_line_name(self):
        #just in case someone opens the budget line in form view
        for record in self:
            computed_name = record.crossovered_budget_id.name
            if record.general_budget_id:
                computed_name += ' - ' + record.general_budget_id.name
            if record.analytic_account_id:
                computed_name += ' - ' + record.analytic_account_id.name
            record.name = computed_name

    def _compute_practical_amount(self):
        def get_accounts(line):
            if line.analytic_account_id:
                return 'account.analytic.line', line.analytic_account_id.plan_id._column_name(), set(line.analytic_account_id.ids)
            return 'account.move.line', 'account_id', set(line.general_budget_id.account_ids.ids)

        def get_query(model, account_fname, date_from, date_to, account_ids):
            domain = [
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                (account_fname, 'in', list(account_ids)),
            ]
            if model == 'account.move.line':
                fname = '-balance'
                general_account = 'account_id'
                domain += [('parent_state', '=', 'posted')]
            else:
                fname = 'amount'
                general_account = 'general_account_id'

            query = self.env[model]._search(domain)
            query.order = None
            query_str, params = query.select('%s', '%s', '%s', '%s', account_fname, general_account, f'SUM({fname})')
            params = [model, account_fname, date_from, date_to] + params
            query_str += f" GROUP BY {account_fname}, {general_account}"

            return query_str, params

        groups = defaultdict(lambda: defaultdict(set))  # {(model, fname): {(date_from, date_to): account_ids}}
        for line in self:
            model, fname, accounts = get_accounts(line)
            groups[(model, fname)][(line.date_from, line.date_to)].update(accounts)

        queries = []
        queries_params = []
        for (model, fname), by_date in groups.items():
            for (date_from, date_to), account_ids in by_date.items():
                query, params = get_query(model, fname, date_from, date_to, account_ids)
                queries.append(query)
                queries_params += params

        self.env.cr.execute(" UNION ALL ".join(queries), queries_params)

        agg_general = defaultdict(lambda: defaultdict(float))  # {(model, date_from, date_to): {(analytic, general): amount}}
        agg_analytic = defaultdict(lambda: defaultdict(float))  # {(model, date_from, date_to): {analytic: amount}}
        for model, fname, date_from, date_to, account_id, general_account_id, amount in self.env.cr.fetchall():
            agg_general[(model, fname, date_from, date_to)][(account_id, general_account_id)] += amount
            agg_analytic[(model, fname, date_from, date_to)][account_id] += amount

        for line in self:
            model, fname, accounts = get_accounts(line)
            general_accounts = line.general_budget_id.account_ids
            if general_accounts:
                line.practical_amount = sum(
                    agg_general.get((model, fname, line.date_from, line.date_to), {}).get((account, general_account), 0)
                    for account in accounts
                    for general_account in general_accounts.ids
                )
            else:
                line.practical_amount = sum(
                    agg_analytic.get((model, fname, line.date_from, line.date_to), {}).get(account, 0)
                    for account in accounts
                )

    @api.depends('date_from', 'date_to')
    def _compute_theoritical_amount(self):
        # beware: 'today' variable is mocked in the python tests and thus, its implementation matter
        today = fields.Date.today()
        for line in self:
            if line.paid_date:
                if today <= line.paid_date:
                    theo_amt = 0.00
                else:
                    theo_amt = line.planned_amount
            else:
                if not line.date_from or not line.date_to:
                    line.theoritical_amount = 0
                    continue
                # One day is added since we need to include the start and end date in the computation.
                # For example, between April 1st and April 30th, the timedelta must be 30 days.
                line_timedelta = line.date_to - line.date_from + timedelta(days=1)
                elapsed_timedelta = today - line.date_from + timedelta(days=1)

                if elapsed_timedelta.days < 0:
                    # If the budget line has not started yet, theoretical amount should be zero
                    theo_amt = 0.00
                elif line_timedelta.days > 0 and today < line.date_to:
                    # If today is between the budget line date_from and date_to
                    theo_amt = (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.planned_amount
                else:
                    theo_amt = line.planned_amount
            line.theoritical_amount = theo_amt

    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount != 0.00:
                line.percentage = float((line.practical_amount or 0.0) / line.theoritical_amount)
            else:
                line.percentage = 0.00

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        # suggesting a budget based on given dates
        domain_list = []
        if self.date_from:
            domain_list.append(['|', ('date_from', '<=', self.date_from), ('date_from', '=', False)])
        if self.date_to:
            domain_list.append(['|', ('date_to', '>=', self.date_to), ('date_to', '=', False)])
        # don't suggest if a budget is already set and verifies condition on its dates
        if domain_list and not self.crossovered_budget_id.filtered_domain(AND(domain_list)):
            self.crossovered_budget_id = self.env['crossovered.budget'].search(AND(domain_list), limit=1)

    @api.onchange('crossovered_budget_id')
    def _onchange_crossovered_budget_id(self):
        if self.crossovered_budget_id:
            self.date_from = self.date_from or self.crossovered_budget_id.date_from
            self.date_to = self.date_to or self.crossovered_budget_id.date_to

    @api.constrains('general_budget_id', 'analytic_account_id')
    def _must_have_analytical_or_budgetary_or_both(self):
        for record in self:
            if not record.analytic_account_id and not record.general_budget_id:
                raise ValidationError(
                    _("You have to enter at least a budgetary position or analytic account on a budget line."))

    def action_open_budget_entries(self):
        if self.analytic_account_id:
            # if there is an analytic account, then the analytic items are loaded
            action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
            action['domain'] = [('auto_account_id', '=', self.analytic_account_id.id),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
            if self.general_budget_id:
                action['domain'] += [('general_account_id', 'in', self.general_budget_id.account_ids.ids)]
        else:
            # otherwise the journal entries booked on the accounts of the budgetary postition are opened
            action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
            action['domain'] = [('account_id', 'in',
                                 self.general_budget_id.account_ids.ids),
                                ('date', '>=', self.date_from),
                                ('date', '<=', self.date_to)
                                ]
        return action

    @api.constrains('date_from', 'date_to')
    def _line_dates_between_budget_dates(self):
        for line in self:
            budget_date_from = line.crossovered_budget_id.date_from
            budget_date_to = line.crossovered_budget_id.date_to
            if line.date_from:
                date_from = line.date_from
                if (budget_date_from and date_from < budget_date_from) or (budget_date_to and date_from > budget_date_to):
                    raise ValidationError(_('"Start Date" of the budget line should be included in the Period of the budget'))
            if line.date_to:
                date_to = line.date_to
                if (budget_date_from and date_to < budget_date_from) or (budget_date_to and date_to > budget_date_to):
                    raise ValidationError(_('"End Date" of the budget line should be included in the Period of the budget'))
