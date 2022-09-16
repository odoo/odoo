# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from random import randint


class AccountAnalyticPlan(models.Model):
    _name = 'account.analytic.plan'
    _description = 'Analytic Plans'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name asc'

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one(
        'account.analytic.plan',
        string="Parent",
        ondelete='cascade',
        domain="[('id', '!=', id), ('company_id', 'in', [False, company_id])]",
    )
    parent_path = fields.Char(
        index='btree',
        unaccent=False,
    )
    children_ids = fields.One2many(
        'account.analytic.plan',
        'parent_id',
        string="Childrens",
    )
    children_count = fields.Integer(
        'Children Plans Count',
        compute='_compute_children_count',
    )
    complete_name = fields.Char(
        'Complete Name',
        compute='_compute_complete_name',
        recursive=True,
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    account_ids = fields.One2many(
        'account.analytic.account',
        'plan_id',
        string="Accounts",
    )
    account_count = fields.Integer(
        'Analytic Accounts Count',
        compute='_compute_analytic_account_count',
    )
    all_account_count = fields.Integer(
        'All Analytic Accounts Count',
        compute='_compute_all_analytic_account_count',
    )
    color = fields.Integer(
        'Color',
        default=_default_color,
    )

    default_applicability = fields.Selection(
        selection=[
            ('optional', 'Optional'),
            ('mandatory', 'Mandatory'),
            ('unavailable', 'Unavailable'),
        ],
        string="Default Applicability",
        required=True,
        default='optional',
        readonly=False,
    )
    applicability_ids = fields.One2many(
        'account.analytic.applicability',
        'analytic_plan_id',
        string='Applicability',
    )

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for plan in self:
            if plan.parent_id:
                plan.complete_name = '%s / %s' % (plan.parent_id.complete_name, plan.name)
            else:
                plan.complete_name = plan.name

    @api.depends('account_ids')
    def _compute_analytic_account_count(self):
        for plan in self:
            plan.account_count = len(plan.account_ids)

    @api.depends('account_ids', 'children_ids')
    def _compute_all_analytic_account_count(self):
        for plan in self:
            plan.all_account_count = self.env['account.analytic.account'].search_count([('plan_id', "child_of", plan.id)])

    @api.depends('children_ids')
    def _compute_children_count(self):
        for plan in self:
            plan.children_count = len(plan.children_ids)

    def action_view_analytical_accounts(self):
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            "domain": [('plan_id', "child_of", self.id)],
            "context": {'default_plan_id': self.id},
            "name": _("Analytical Accounts"),
            'view_mode': 'list,form',
        }
        return result

    def action_view_children_plans(self):
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.plan",
            "domain": [('id', 'in', self.children_ids.ids)],
            "context": {'default_parent_id': self.id,
                        'default_color': self.color},
            "name": _("Analytical Plans"),
            'view_mode': 'list,form',
        }
        return result

    @api.model
    def get_relevant_plans(self, **kwargs):
        """ Returns the list of plans that should be available.
            This list is computed based on the applicabilities of root plans. """
        list_plans = []
        set_plan_ids = {}
        all_plans = self.search([('parent_id', '=', False), '|', ('account_ids', '!=', False), ('children_ids.account_ids', '!=', False)])
        for plan in all_plans:
            applicability = plan._get_applicability(**kwargs)
            if applicability != 'unavailable':
                set_plan_ids[plan.id] = plan
                list_plans.append(
                    {
                        "id": plan.id,
                        "name": plan.name,
                        "color": plan.color,
                        "applicability": applicability,
                        "all_account_count": plan.all_account_count
                    })
        # If we have accounts that are already selected (before the applicability rules changed or from a model),
        # we want the plans that were unavailable to be shown in the list (and in optional, because the previous
        # percentage could be different from 0)
        record_account_ids = kwargs.get('existing_account_ids', [])
        forced_plans = self.env['account.analytic.account'].browse(record_account_ids).mapped('root_plan_id')
        for plan in forced_plans.filtered(lambda plan: plan.id not in set_plan_ids):
            list_plans.append({
                    "id": plan.id,
                    "name": plan.name,
                    "color": plan.color,
                    "applicability": 'optional',
                    "all_account_count": plan.all_account_count
                })
        return sorted(list_plans, key=lambda d: (d['applicability'], d['id']))

    def _get_applicability(self, **kwargs):
        """ Returns the applicability of the best applicability line or the default applicability """
        self.ensure_one()
        if 'applicability' in kwargs:
            # For models for example, we want all plans to be visible, so we force the applicability
            return kwargs['applicability']
        else:
            score = 0
            applicability = self.default_applicability
            for applicability_rule in self.applicability_ids:
                score_rule = applicability_rule._get_score(**kwargs)
                if score_rule > score:
                    applicability = applicability_rule.applicability
                    score = score_rule
            return applicability

    def _get_default(self):
        plan = self.env['account.analytic.plan'].sudo().search(
            ['|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)],
            limit=1)
        if plan:
            return plan
        else:
            return self.env['account.analytic.plan'].create({
                'name': 'Default',
                'company_id': self.env.company.id,
            })


class AccountAnalyticApplicability(models.Model):
    _name = 'account.analytic.applicability'
    _description = "Analytic Plan's Applicabilities"

    analytic_plan_id = fields.Many2one('account.analytic.plan')
    business_domain = fields.Selection(
        selection=[
            ('general', 'Miscellaneous'),
        ],
        required=True,
        string='Domain',
    )
    applicability = fields.Selection([
        ('optional', 'Optional'),
        ('mandatory', 'Mandatory'),
        ('unavailable', 'Unavailable'),
    ],
        required=True,
        string="Applicability",
    )

    def _get_score(self, **kwargs):
        """ Gives the score of an applicability with the parameters of kwargs """
        self.ensure_one()
        if not kwargs.get('business_domain'):
            return 0
        else:
            return 1 if kwargs.get('business_domain') == self.business_domain else -1
