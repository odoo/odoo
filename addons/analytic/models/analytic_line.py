# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml.builder import E

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv.expression import OR


class AnalyticPlanFieldsMixin(models.AbstractModel):
    """ Add one field per analytic plan to the model """
    _name = 'analytic.plan.fields.mixin'
    _description = 'Analytic Plan Fields'

    account_id = fields.Many2one(
        'account.analytic.account',
        'Project Account',
        ondelete='restrict',
        index=True,
        check_company=True,
    )
    # Magic column that represents all the plans at the same time, except for the compute
    # where it is context dependent, and needs the id of the desired plan.
    # Used as a syntactic sugar for search views, and magic field for one2many relation
    auto_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        compute='_compute_auto_account',
        inverse='_inverse_auto_account',
        search='_search_auto_account',
    )

    @api.depends_context('analytic_plan_id')
    def _compute_auto_account(self):
        plan = self.env['account.analytic.plan'].browse(self.env.context.get('analytic_plan_id'))
        for line in self:
            line.auto_account_id = bool(plan) and line[plan._column_name()]

    def _inverse_auto_account(self):
        for line in self:
            line[line.auto_account_id.plan_id._column_name()] = line.auto_account_id

    def _search_auto_account(self, operator, value):
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        return OR([
            [(plan._column_name(), operator, value)]
            for plan in project_plan + other_plans
        ])

    def _get_plan_fnames(self):
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        return [fname for plan in project_plan + other_plans if (fname := plan._column_name()) in self]

    def _get_analytic_accounts(self):
        return self.env['account.analytic.account'].browse([
            self[fname].id
            for fname in self._get_plan_fnames()
            if self[fname]
        ])

    def _get_analytic_distribution(self):
        account_ids = self._get_analytic_accounts().ids
        return {} if not account_ids else {",".join(str(account_id) for account_id in account_ids): 100}

    def _get_mandatory_plans(self, company, business_domain):
        return [
            {
                'name': plan['name'],
                'column_name': plan['column_name'],
            }
            for plan in self.env['account.analytic.plan']
                .sudo().with_company(company)
                .get_relevant_plans(business_domain=business_domain, company_id=company.id)
            if plan['applicability'] == 'mandatory'
        ]

    def _get_plan_domain(self, plan):
        return [('plan_id', 'child_of', plan.id)]

    def _get_account_node_context(self, plan):
        return {'default_plan_id': plan.id}

    @api.constrains(lambda self: self._get_plan_fnames())
    def _check_account_id(self):
        fnames = self._get_plan_fnames()
        for line in self:
            if not any(line[fname] for fname in fnames):
                raise ValidationError(_("At least one analytic account must be set"))

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields = super().fields_get(allfields, attributes)
        if not self._context.get("studio") and self.env['account.analytic.plan'].has_access('read'):
            project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
            for plan in project_plan + other_plans:
                fname = plan._column_name()
                if fname in fields:
                    fields[fname]['string'] = plan.name
                    fields[fname]['domain'] = repr(self._get_plan_domain(plan))
        return fields

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        return self._patch_view(arch, view, view_type)

    def _patch_view(self, arch, view, view_type):
        if not self._context.get("studio") and self.env['account.analytic.plan'].has_access('read'):
            project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()

            # Find main account nodes
            account_node = arch.find('.//field[@name="account_id"]')
            account_filter_node = arch.find('.//filter[@name="account_id"]')

            # Force domain on main account node as the fields_get doesn't do the trick
            if account_node is not None and view_type == 'search':
                account_node.set('domain', repr(self._get_plan_domain(project_plan)))

            # If there is a main node, append the ones for other plans
            if account_node is not None or account_filter_node is not None:
                account_node.set('context', repr(self._get_account_node_context(project_plan)))
                for plan in other_plans[::-1]:
                    fname = plan._column_name()
                    if account_node is not None:
                        account_node.addnext(E.field(**{
                            'optional': 'show',
                            **account_node.attrib,
                            'name': fname,
                            'domain': repr(self._get_plan_domain(plan)),
                            'context': repr(self._get_account_node_context(plan)),
                        }))
                    if account_filter_node is not None:
                        account_filter_node.addnext(E.filter(name=fname, context=f"{{'group_by': '{fname}'}}"))
        return arch, view


class AccountAnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['analytic.plan.fields.mixin']
    _description = 'Analytic Line'
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        'Description',
        required=True,
    )
    date = fields.Date(
        'Date',
        required=True,
        index=True,
        default=fields.Date.context_today,
    )
    amount = fields.Monetary(
        'Amount',
        required=True,
        default=0.0,
    )
    unit_amount = fields.Float(
        'Quantity',
        default=0.0,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        check_company=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.context.get('user_id', self.env.user.id),
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
        store=True,
        compute_sudo=True,
    )
    category = fields.Selection(
        [('other', 'Other')],
        default='other',
    )
