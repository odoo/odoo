# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from lxml.builder import E

from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.exceptions import ValidationError
from odoo.fields import Domain


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

    def _compute_partner_id(self):
        # TO OVERRIDE
        pass

    def _inverse_auto_account(self):
        for line in self:
            line[line.auto_account_id.plan_id._column_name()] = line.auto_account_id

    def _search_auto_account(self, operator, value):
        if Domain.is_negative_operator(operator):
            return NotImplemented
        project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        return Domain.OR([
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

    def _get_distribution_key(self):
        return ",".join(str(account_id) for account_id in self._get_analytic_accounts().ids)

    def _get_analytic_distribution(self):
        accounts = self._get_distribution_key()
        return {} if not accounts else {accounts: 100}

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
            if account_node is not None:
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
                for plan in other_plans[::-1] + project_plan:
                    fname = plan._column_name()
                    if plan != project_plan:
                        account_filter_node.addnext(E.filter(name=fname, context=f"{{'group_by': '{fname}'}}"))
                    current = plan
                    while current := current.children_ids:
                        _depth, subfname = current[0]._hierarchy_name()
                        if subfname in self._fields:
                            account_filter_node.addnext(E.filter(name=subfname, context=f"{{'group_by': '{subfname}'}}"))
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
    fiscal_year_search = fields.Boolean(
        search='_search_fiscal_date',
        store=False, exportable=False,
        export_string_translation=False,
    )
    analytic_distribution = fields.Json(
        'Analytic Distribution',
        compute="_compute_analytic_distribution",
        inverse='_inverse_analytic_distribution',
    )
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )

    def _compute_analytic_distribution(self):
        for line in self:
            line.analytic_distribution = {line._get_distribution_key(): 100}

    def _inverse_analytic_distribution(self):
        empty_account = dict.fromkeys(self._get_plan_fnames(), False)
        to_create_vals = []
        for line in self:
            final_distribution = self.env['analytic.mixin']._merge_distribution(
                {line._get_distribution_key(): 100},
                line.analytic_distribution or {},
            )
            amount_fname = line._split_amount_fname()
            vals_list = [
                {amount_fname: line[amount_fname] * percent / 100} | empty_account | {
                    account.plan_id._column_name(): account.id
                    for account in self.env['account.analytic.account'].browse(int(aid) for aid in account_ids.split(','))
                }
                for account_ids, percent in final_distribution.items()
            ]

            line.write(vals_list[0])
            to_create_vals += [line.copy_data(vals)[0] for vals in vals_list[1:]]
        if to_create_vals:
            self.create(to_create_vals)
            self.env.user._bus_send('simple_notification', {
                'type': 'success',
                'message': self.env._("%s analytic lines created", len(to_create_vals)),
            })

    def _split_amount_fname(self):
        return 'amount'

    def _search_fiscal_date(self, operator, value):
        fiscalyear_date_range = self.env.company.compute_fiscalyear_dates(fields.Date.today())
        return [('date', '>=', fiscalyear_date_range['date_from'] - relativedelta(years=1))]
