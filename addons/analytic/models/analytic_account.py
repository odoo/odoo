# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError


class AccountAnalyticDistribution(models.Model):
    _name = 'account.analytic.distribution'
    _description = 'Analytic Account Distribution'
    _rec_name = 'account_id'

    account_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=True)
    percentage = fields.Float(string='Percentage', required=True, default=100.0)
    name = fields.Char(string='Name', readonly=True)

    _sql_constraints = [
        ('check_percentage', 'CHECK(percentage >= 0 AND percentage <= 100)',
         'The percentage of an analytic distribution should be between 0 and 100.')
    ]

    def name_get(self):
        result = []
        for distrib in self:
            if distrib.percentage == 100:
                result.append(distrib.account_id.name)
            else:
                result.append("%s : %d%%" % (distrib.account_id.name, distrib.percentage))
        return result


class AccountAnalyticPlan(models.Model):
    _name = 'account.analytic.plan'
    _description = 'Analytic Plans'
    _parent_store = True
    _rec_name = 'complete_name'

    name = fields.Char(required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('account.analytic.plan', string="Parent", ondelete='cascade', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    parent_path = fields.Char(index='btree', unaccent=False)
    children_ids = fields.One2many('account.analytic.plan', 'parent_id', string="Childrens")
    children_count = fields.Integer('Children Plans Count', compute='_compute_children_count')
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', recursive=True, store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    account_ids = fields.One2many('account.analytic.account', 'plan_id', string="Accounts")
    account_count = fields.Integer('Analytic Accounts Count', compute='_compute_analytic_account_count')
    root_parent_id = fields.Many2one('account.analytic.plan', string="Root Parent", compute="_compute_root_parent", recursive=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    all_children_ids = fields.One2many('account.analytic.plan', 'root_parent_id', string="All Childrens")

    @api.depends('parent_id', 'parent_id.root_parent_id')
    def _compute_root_parent(self):
        for plan in self:
            if plan.parent_id:
                if plan.parent_id.root_parent_id:
                    plan.root_parent_id = plan.parent_id.root_parent_id
                else:
                    plan.root_parent_id = plan.parent_id
            else:
                plan.root_parent_id = None

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

    @api.depends('children_ids')
    def _compute_children_count(self):
        for plan in self:
            plan.children_count = len(plan.children_ids)

    def action_view_analytical_accounts(self):
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.analytic.account",
            "domain": [('id', 'in', self.account_ids.ids)],
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
            "context": {'default_parent_id': self.id},
            "name": _("Analytical Plans"),
            'view_mode': 'list,form',
        }
        return result


class AccountAnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'code, name asc'
    _check_company_auto = True
    _rec_names_search = ['name', 'code', 'partner_id']

    name = fields.Char(string='Analytic Account', index='trigram', required=True, tracking=True)
    code = fields.Char(string='Reference', index='btree', tracking=True)
    active = fields.Boolean('Active', help="If the active field is set to False, it will allow you to hide the account without removing it.", default=True)

    plan_id = fields.Many2one('account.analytic.plan', string='Plan', check_company=True, required=True,
                               default=lambda self: self.env.company.analytic_plan_id if 'analytic_plan_id' in self.env.company._fields else self.env.ref('analytic.analytic_plan_default').id)
    root_plan_id = fields.Many2one('account.analytic.plan', string='Root Plan', check_company=True,
                                   compute="_compute_root_plan")

    line_ids = fields.One2many('account.analytic.line', 'account_id', string="Analytic Lines")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # use auto_join to speed up name_search call
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True, tracking=True, check_company=True)

    balance = fields.Monetary(compute='_compute_debit_credit_balance', string='Balance',  groups='account.group_account_readonly')
    debit = fields.Monetary(compute='_compute_debit_credit_balance', string='Debit', groups='account.group_account_readonly')
    credit = fields.Monetary(compute='_compute_debit_credit_balance', string='Credit', groups='account.group_account_readonly')

    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    def name_get(self):
        res = []
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name = '[' + analytic.code + '] ' + name
            if analytic.partner_id.commercial_partner_id.name:
                name = name + ' - ' + analytic.partner_id.commercial_partner_id.name
            res.append((analytic.id, name))
        return res

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

    @api.depends('plan_id', 'plan_id.root_parent_id')
    def _compute_root_plan(self):
        for account in self:
            account.root_plan_id = account.plan_id if not account.plan_id.root_parent_id else account.plan_id.root_parent_id


class AccountAnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc, id desc'
    _check_company_auto = True

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Description', required=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    amount = fields.Monetary('Amount', required=True, default=0.0)
    unit_amount = fields.Float('Quantity', default=0.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_uom_id.category_id', string='UoM Category', readonly=True)
    account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='restrict', index=True, check_company=True)
    partner_id = fields.Many2one('res.partner', string='Partner', check_company=True)
    user_id = fields.Many2one('res.users', string='User', default=_default_user, index=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True, store=True, compute_sudo=True)
    plan_id = fields.Many2one('account.analytic.plan', related='account_id.plan_id', store=True, readonly=True, compute_sudo=True)
    category = fields.Selection([('other', 'Other')], default='other')

    @api.constrains('company_id', 'account_id')
    def _check_company_id(self):
        for line in self:
            if line.account_id.company_id and line.company_id.id != line.account_id.company_id.id:
                raise ValidationError(_('The selected account belongs to another company than the one you\'re trying to create an analytic item for'))
