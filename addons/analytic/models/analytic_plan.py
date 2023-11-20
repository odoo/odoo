# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import ormcache


class AccountAnalyticPlan(models.Model):
    _name = 'account.analytic.plan'
    _description = 'Analytic Plans'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'sequence asc, id'

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char(
        required=True,
        translate=True,
        inverse='_inverse_name',
    )
    description = fields.Text(string='Description')
    parent_id = fields.Many2one(
        'account.analytic.plan',
        string="Parent",
        inverse='_inverse_parent_id',
        ondelete='cascade',
        domain="['!', ('id', 'child_of', id)]",
    )
    parent_path = fields.Char(
        index='btree',
        unaccent=False,
    )
    root_id = fields.Many2one(
        'account.analytic.plan',
        compute='_compute_root_id',
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
    sequence = fields.Integer(default=10)

    default_applicability = fields.Selection(
        selection=[
            ('optional', 'Optional'),
            ('mandatory', 'Mandatory'),
            ('unavailable', 'Unavailable'),
        ],
        string="Default Applicability",
        required=True,
        default='optional',  # actually set in _auto_init because company dependent
        readonly=False,
        company_dependent=True,
    )
    applicability_ids = fields.One2many(
        'account.analytic.applicability',
        'analytic_plan_id',
        string='Applicability',
        domain="[('company_id', '=', current_company_id)]",
    )

    def _auto_init(self):
        super()._auto_init()
        def precommit():
            self.env['ir.property']._set_default(
                name='default_applicability',
                model=self._name,
                value='optional',
            )
        self.env.cr.precommit.add(precommit)

    @ormcache()
    def __get_all_plans(self):
        project_plan = self.browse(int(self.env['ir.config_parameter'].sudo().get_param('analytic.project_plan', 0)))
        if not project_plan:
            raise UserError(_("A 'Project' plan needs to exist and its id needs to be set as `analytic.project_plan` in the system variables"))
        other_plans = self.sudo().search([('parent_id', '=', False)]) - project_plan
        return project_plan.id, other_plans.ids

    def _get_all_plans(self):
        return map(self.browse, self.__get_all_plans())

    def _strict_column_name(self):
        self.ensure_one()
        project_plan, _other_plans = self._get_all_plans()
        return 'account_id' if self == project_plan else f"x_plan{self.id}_id"

    def _column_name(self):
        return self.root_id._strict_column_name()

    def _inverse_name(self):
        self._sync_plan_column()

    def _inverse_parent_id(self):
        self._sync_plan_column()

    @api.depends('parent_id', 'parent_path')
    def _compute_root_id(self):
        for plan in self:
            plan.root_id = int(plan.parent_path[:-1].split('/')[0]) if plan.parent_path else plan

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
        plans_count = dict(
            self.env['account.analytic.account']._read_group(
                domain=[('root_plan_id', 'in', self.ids)],
                aggregates=['id:count'],
                groupby=['root_plan_id']
            )
        )
        for plan in self:
            plan.all_account_count = plans_count.get(plan, 0)

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
            "domain": [('parent_id', '=', self.id)],
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
        record_account_ids = kwargs.get('existing_account_ids', [])
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        root_plans = (project_plan + other_plans).filtered(lambda p: (
            p.all_account_count > 0
            and not p.parent_id
            and p._get_applicability(**kwargs) != 'unavailable'
        ))
        # If we have accounts that are already selected (before the applicability rules changed or from a model),
        # we want the plans that were unavailable to be shown in the list (and in optional, because the previous
        # percentage could be different from 0)
        forced_plans = self.env['account.analytic.account'].browse(record_account_ids).exists().mapped(
            'root_plan_id') - root_plans
        return [
            {
                "id": plan.id,
                "name": plan.name,
                "color": plan.color,
                "applicability": plan._get_applicability(**kwargs) if plan in root_plans else 'optional',
                "all_account_count": plan.all_account_count
            }
            for plan in (root_plans + forced_plans).sorted('sequence')
        ]

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

    def unlink(self):
        # Remove the dynamic field created with the plan (see `_inverse_name`)
        self._find_plan_column().unlink()
        return super().unlink()

    def _find_plan_column(self):
        return self.env['ir.model.fields'].search([
            ('name', 'in', [plan._strict_column_name() for plan in self]),
            ('model', '=', 'account.analytic.line'),
        ])

    def _sync_plan_column(self):
        # Create/delete a new field/column on analytic lines for this plan, and keep the name in sync.
        for plan in self:
            prev = plan._find_plan_column()
            if plan.parent_id and prev:
                prev.unlink()
            elif prev:
                prev.field_description = plan.name
            elif not plan.parent_id:
                self.env['ir.model.fields'].with_context(update_custom_fields=True).create({
                    'name': plan._strict_column_name(),
                    'field_description': plan.name,
                    'state': 'manual',
                    'model': 'account.analytic.line',
                    'model_id': self.env['ir.model']._get_id('account.analytic.line'),
                    'ttype': 'many2one',
                    'relation': 'account.analytic.account',
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
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    def _get_score(self, **kwargs):
        """ Gives the score of an applicability with the parameters of kwargs """
        self.ensure_one()
        if not kwargs.get('business_domain'):
            return 0
        else:
            return 1 if kwargs.get('business_domain') == self.business_domain else -1
