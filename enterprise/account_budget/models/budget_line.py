# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BudgetLine(models.Model):
    _name = 'budget.line'
    _inherit = 'analytic.plan.fields.mixin'
    _description = "Budget Line"
    _order = 'sequence, id'

    name = fields.Char(related='budget_analytic_id.name', string='Budget Name')
    sequence = fields.Integer('Sequence', default=10)
    budget_analytic_id = fields.Many2one('budget.analytic', 'Budget Analytic', ondelete='cascade', index=True, required=True)
    date_from = fields.Date('Start Date', related='budget_analytic_id.date_from', store=True)
    date_to = fields.Date('End Date', related='budget_analytic_id.date_to', store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    budget_amount = fields.Monetary(
        string='Budgeted')
    achieved_amount = fields.Monetary(
        compute='_compute_all',
        string='Achieved',
        help="Amount Billed/Invoiced.")
    achieved_percentage = fields.Float(
        compute='_compute_all',
        string='Achieved (%)')
    committed_amount = fields.Monetary(
        compute='_compute_all',
        string='Committed',
        help="Already Billed amount + Confirmed purchase orders.")
    committed_percentage = fields.Float(
        compute='_compute_all',
        string='Committed (%)')
    theoritical_amount = fields.Monetary(
        compute='_compute_theoritical_amount',
        string='Theoretical',
        help="Amount supposed to be Billed/Invoiced, formula = (Budget Amount / Budget Days) x Budget Days Completed")
    theoritical_percentage = fields.Float(
        compute='_compute_theoritical_amount',
        string='Theoretical (%)',
        aggregator='avg')
    company_id = fields.Many2one(related='budget_analytic_id.company_id', comodel_name='res.company', string='Company', store=True, readonly=True)
    is_above_budget = fields.Boolean(compute='_compute_above_budget')
    budget_analytic_state = fields.Selection(related='budget_analytic_id.state', string='Budget State', store=True, readonly=True)

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for line in self:
            if line.date_from and line.date_to and line.date_to < line.date_from:
                raise ValidationError(_("The 'End Date' must be greater than or equal to 'Start Date'."))

    @api.depends('achieved_amount', 'budget_amount')
    def _compute_above_budget(self):
        for line in self:
            line.is_above_budget = line.achieved_amount > line.budget_amount

    def _compute_all(self):
        grouped = {
            line: (committed, achieved)
            for line, committed, achieved in self.env['budget.report'].with_context(budget_report_budget_line_ids=self.ids)._read_group(
                domain=[('budget_line_id', 'in', self.ids)],
                groupby=['budget_line_id'],
                aggregates=['committed:sum', 'achieved:sum'],
            )
        }
        for line in self:
            committed, achieved = grouped.get(line, (0, 0))
            line.committed_amount = committed
            line.achieved_amount = achieved
            line.committed_percentage = line.budget_amount and (line.committed_amount / line.budget_amount)
            line.achieved_percentage = line.budget_amount and (line.achieved_amount / line.budget_amount)

    @api.depends('date_from', 'date_to')
    def _compute_theoritical_amount(self):
        today = fields.Date.context_today(self)
        for line in self:
            if not line.date_from or not line.date_to:
                line.theoritical_amount = 0
                line.theoritical_percentage = 0
                continue
            # One day is added since we need to include the start and end date in the computation.
            # For example, between April 1st and April 30th, the timedelta must be 30 days.
            line_timedelta = line.date_to - line.date_from + timedelta(days=1)
            elapsed_timedelta = min(max(today, line.date_from), line.date_to) - line.date_from + timedelta(days=1)
            line.theoritical_amount = line_timedelta and (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.budget_amount
            line.theoritical_percentage = line.budget_amount and (line.theoritical_amount / line.budget_amount)

    def _read_group_select(self, aggregate_spec, query):
        # flag achieved_amount/theoritical_amount as aggregatable
        # and manually sum the values from the records in the group
        if aggregate_spec in ('achieved_amount:sum', 'theoritical_amount:sum', 'theoritical_percentage:avg'):
            return super()._read_group_select('id:recordset', query)
        return super()._read_group_select(aggregate_spec, query)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        if aggregate_spec in ('achieved_amount:sum', 'theoritical_amount:sum', 'theoritical_percentage:avg'):
            field_name, op = aggregate_spec.split(':')
            column = super()._read_group_postprocess_aggregate('id:recordset', raw_values)
            if op == 'sum':
                return (sum(records.mapped(field_name)) for records in column)
            if op == 'avg':
                return (sum(records.mapped(field_name)) / len(records) for records in column)
        return super()._read_group_postprocess_aggregate(aggregate_spec, raw_values)

    def action_open_budget_entries(self):
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        all_plan = project_plan + other_plans
        domain = [('budget_analytic_id', '=', self.budget_analytic_id.id), ('budget_line_id', '=', self.id)]
        for plan in all_plan:
            fname = plan._column_name()
            if self[fname]:
                domain += [(fname, 'in', self[fname].ids)]
        action = self.env['ir.actions.act_window']._for_xml_id('account_budget.budget_report_action')
        action['domain'] = domain
        return action
