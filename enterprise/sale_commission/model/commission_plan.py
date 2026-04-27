# Part of Odoo. See LICENSE file for full copyright and licensing details.


import json

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError


class CommissionPlan(models.Model):
    _name = 'sale.commission.plan'
    _description = 'Commission Plan'
    _order = 'id'
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    name = fields.Char("Name", required=True)

    date_from = fields.Date("From", required=True, default=lambda self: fields.Date.today() + relativedelta(day=1, month=1), tracking=True)
    date_to = fields.Date("To", required=True, default=lambda self: fields.Date.today() + relativedelta(years=1, day=1, month=1) - relativedelta(days=1), tracking=True)
    periodicity = fields.Selection([('month', "Monthly"), ('quarter', "Quarterly"), ('year', "Yearly")], required=True, default='quarter', tracking=True)

    commission_amount = fields.Monetary("On Target Commission", help='OTC', currency_field='currency_id', default=1000)

    type = fields.Selection([('target', "Targets"), ('achieve', "Achievements")], required=True, default='achieve', tracking=True)
    user_type = fields.Selection([('person', "Salesperson"), ('team', "Sales Team")], required=True, default='person', tracking=True)
    team_id = fields.Many2one('crm.team', 'Sale team')

    achievement_ids = fields.One2many('sale.commission.plan.achievement', 'plan_id', default=[Command.create({'type': 'amount_invoiced'})], copy=True)
    target_ids = fields.One2many('sale.commission.plan.target', 'plan_id', compute='_compute_targets',
                                 store=True, readonly=False)
    target_commission_ids = fields.One2many('sale.commission.plan.target.commission', 'plan_id',
                                            compute='_compute_target_commission_ids',
                                            inverse='_inverse_target_commission_ids',
                                            store=True, readonly=False, copy=True)
    target_commission_graph = fields.Text(compute="_compute_target_commission_graph")
    user_ids = fields.One2many('sale.commission.plan.user', 'plan_id', copy=True)

    state = fields.Selection([('draft', "Draft"), ('approved', "Approved"), ('done', "Done"), ('cancel', "Cancelled")],
                             required=True, default='draft', tracking=True)

    def init(self):
        self.env.cr.execute("""
CREATE INDEX IF NOT EXISTS sale_order_team_id_date_order_idx ON sale_order (team_id, date_order) WHERE state = 'sale';
CREATE INDEX IF NOT EXISTS account_move_team_id_date_idx ON account_move (team_id, date) WHERE move_type IN ('out_invoice', 'out_refund');
CREATE INDEX IF NOT EXISTS account_move_invoice_user_id_date_idx ON account_move (invoice_user_id, date) WHERE move_type IN ('out_invoice', 'out_refund');
        """)
        super().init()

    @api.constrains('target_commission_ids')
    def _constrains_target_commission_ids(self):
        for plan in self:
            if plan.type == 'target' and not plan.target_commission_ids.filtered(lambda target: target.target_rate == 0):
                raise ValidationError(_("The plan should have at least one target with an achievement rate of 0%"))

    @api.constrains('date_from', 'date_to')
    def _date_constraint(self):
        for plan in self:
            if not plan.date_to > plan.date_from:
                raise ValidationError(_("The start date must be before the end date."))

    @api.constrains('team_id', 'user_type')
    def _constrains_team_id(self):
        for plan in self:
            if plan.user_type == 'team' and not plan.team_id:
                raise ValidationError(_("The team is required in team plan."))

    @api.model
    def _date2name(self, dt, periodicity):
        if periodicity == 'month':
            return dt.strftime('%b %Y')
        elif periodicity == 'quarter':
            return f'{dt.year} Q{(dt.month // 3) + 1}'
        elif periodicity == 'year':
            return dt.strftime('%Y')
        return ''

    @api.depends('periodicity', 'date_from', 'date_to', 'type')
    def _compute_targets(self, amount=0):
        for plan in self:
            if not plan.date_from or not plan.date_to:
                continue
            date_from = plan.date_from
            if plan.periodicity == 'month':
                timedelta = relativedelta(months=1, day=1)
                date_from = date_from - relativedelta(days=1) + timedelta
            elif plan.periodicity == 'quarter':
                timedelta = relativedelta(months=3, day=1)
                r_delta = relativedelta(month=(date_from.month // 3) * 3 + 1, day=1)
                if r_delta.month >12:
                     d1 = r_delta.month - 12
                     r_delta = relativedelta(year=1, day=1) + relativedelta(month=d1, day=1)
                start_date = date_from + r_delta
                while start_date < date_from:
                    start_date += timedelta
                date_from = start_date
            else:
                timedelta = relativedelta(years=1, month=1, day=1)
                date_from = date_from - relativedelta(days=1) + timedelta

            targets = [Command.clear()]
            while date_from + timedelta - relativedelta(days=1) <= plan.date_to:
                targets += [Command.create({
                    'name': self._date2name(date_from, plan.periodicity),
                    'date_from': date_from,
                    'date_to': date_from + timedelta - relativedelta(days=1),
                    'amount': amount,
                })]
                date_from += timedelta
            plan.target_ids = targets

    @api.depends('commission_amount', 'type')
    def _compute_target_commission_ids(self):
        for plan in self:
            if plan.type != 'target':
                continue
            elif not plan.target_commission_ids:
                plan.target_commission_ids = [Command.create({
                    'plan_id': plan.id,
                    'target_rate': 0,
                    'amount': 0,
                }), Command.create({
                    'plan_id': plan.id,
                    'target_rate': 0.5,
                    'amount': 0,
                }), Command.create({
                    'plan_id': plan.id,
                    'target_rate': 1,
                    'amount': plan.commission_amount or 1,
                    'amount_rate': 1,
                })]
            else:
                for target in plan.target_commission_ids:
                    target.amount = target.amount_rate * plan.commission_amount

    def _inverse_target_commission_ids(self):
        for plan in self:
            sorted_amounts = {}
            sorted_rates = []
            exact_value = False
            for target in plan.target_commission_ids.sorted('target_rate'):
                sorted_amounts[target.target_rate] = target.amount
                sorted_rates.append(target.target_rate)
                if target.target_rate == 1 and target.amount:
                    plan.commission_amount = target.amount
                    exact_value = True
                    break
            if not exact_value:
                # Try to interpolate/extrapolate values at 100
                amount = self._get_completion_value(sorted_amounts, sorted_rates)
                if amount:
                    plan.commission_amount = amount

    @api.depends('target_commission_ids')
    def _compute_target_commission_graph(self):
        for plan in self:
            plan.target_commission_graph = json.dumps(plan._get_graph_data())

    def _get_graph_data(self):
        self.ensure_one()
        values = []
        for target in self.target_commission_ids.sorted('target_rate'):
            values += [{'x': round(target.target_rate * 100), 'y': target.amount}]
        if values:
            # For visual purpose: explain how values is computed outside of known bounds
            values += [{'x': values[-1]['x'] + 50, 'y': values[-1]['y']}]
        return {'values': values, 'currency': self.currency_id.symbol}

    def action_open_commission(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.commission.report",
            "name": _("Related commissions"),
            "views": [[self.env.ref('sale_commission.sale_commission_report_view_list').id, "list"]],
            "domain": [('plan_id', '=', self.id)],
        }

    @staticmethod
    def _extract_past_users(user_ids):
        today = fields.Date.today()
        return [user for user in user_ids if len(user) == 3 and not user[2].get('date_to') or user[2]['date_to'] >= today]

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=_("%s (copy)", cp.name), user_ids=self._extract_past_users(vals.get('user_ids', [])))
            for cp, vals in zip(self, vals_list)
        ]

    def action_approve(self):
        self.state = 'approved'

    def action_draft(self):
        self.state = 'draft'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    @api.model
    def _get_completion_value(self, sorted_amounts, sorted_rates):
        """ Interpolate/extrapolate the amount at 100% target completion.
        return: amount at 100% target completion
        """
        lowest_vals = [v for v in sorted_rates if v < 1]
        higher_vals = [v for v in sorted_rates if v > 1]
        # The plan has always a value at 0% completion
        low, high = None, None
        if lowest_vals and higher_vals:
            low = lowest_vals[-1]
            high = higher_vals[0]
        elif not higher_vals and len(lowest_vals) > 1:
            low = lowest_vals[-2]
            high = lowest_vals[-1]
        if not (low and high) or low == high:
            # No values or division by zero
            return
        # y = ax + b
        return sorted_amounts[low] + (sorted_amounts[high] - sorted_amounts[low])/(high-low) * (1-low)
