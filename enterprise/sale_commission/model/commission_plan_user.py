# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import Command, models, fields, exceptions, _, api


class CommissionPlanUser(models.Model):
    _name = 'sale.commission.plan.user'
    _description = 'Commission Plan User'
    _order = 'id'

    plan_id = fields.Many2one('sale.commission.plan', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', "Salesperson", required=True, domain="[('share', '=', False)]")

    date_from = fields.Date("From", compute='_compute_date_from', store=True, readonly=False)
    date_to = fields.Date("To")

    other_plans = fields.Many2many('sale.commission.plan', string="Other plans", compute='_compute_other_plans', readonly=False)

    _sql_constraints = [
        ('user_uniq', 'unique (plan_id, user_id)', "The user is already present in the plan"),
    ]

    @api.constrains('date_from', 'date_to')
    def _date_constraint(self):
        for user in self:
            if user.date_to and user.date_from and user.date_to < user.date_from:
                raise exceptions.UserError(_("From must be before To"))
            if user.date_from and user.plan_id.date_from and user.date_from < user.plan_id.date_from:
                raise exceptions.UserError(_("User period cannot start before the plan."))
            if user.date_to and user.plan_id.date_to and user.date_to > user.plan_id.date_to:
                raise exceptions.UserError(_("User period cannot end after the plan."))

    @api.depends('user_id', 'plan_id.date_from', 'plan_id.date_to', 'date_from', 'date_to')
    def _compute_other_plans(self):
        plan_ids = self.search([
            ('user_id', 'in', self.user_id.ids),
            ('plan_id.state', 'in', ['draft', 'approved']),
        ]).plan_id
        for pu in self:
            pu_date_from = pu.date_from or pu.plan_id.date_from
            pu_date_to = pu.date_to or pu.plan_id.date_to
            other_plans_ids = []
            for plan in (plan_ids - pu.plan_id._origin -pu.plan_id):
                if plan.date_to < pu_date_from or plan.date_from > pu_date_to:
                    # no overlap
                    continue
                other_plans_ids.append(plan.id)
            pu.other_plans = [Command.clear()] if not other_plans_ids else [Command.set(other_plans_ids)]

    @api.depends('plan_id')
    def _compute_date_from(self):
        today = fields.Date.today()
        for user in self:
            if user.date_from:
                return
            if not user.plan_id.date_from:
                return
            user.date_from = max(user.plan_id.date_from, today) if user.plan_id.state != 'draft' else user.plan_id.date_from
