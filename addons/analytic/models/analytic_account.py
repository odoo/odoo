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
    name = fields.Char(string='Name', related='account_id.name', readonly=False)
    tag_id = fields.Many2one('account.analytic.tag', string="Parent tag", required=True)

    _sql_constraints = [
        ('check_percentage', 'CHECK(percentage >= 0 AND percentage <= 100)',
         'The percentage of an analytic distribution should be between 0 and 100.')
    ]

class AccountAnalyticTag(models.Model):
    _name = 'account.analytic.tag'
    _description = 'Analytic Tags'
    name = fields.Char(string='Analytic Tag', index=True, required=True)
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True, help="Set active to false to hide the Analytic Tag without removing it.")
    active_analytic_distribution = fields.Boolean('Analytic Distribution')
    analytic_distribution_ids = fields.One2many('account.analytic.distribution', 'tag_id', string="Analytic Accounts")
    company_id = fields.Many2one('res.company', string='Company')

class AccountAnalyticGroup(models.Model):
    _name = 'account.analytic.group'
    _description = 'Analytic Categories'
    _parent_store = True
    _rec_name = 'complete_name'

    name = fields.Char(required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('account.analytic.group', string="Parent", ondelete='cascade', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    parent_path = fields.Char(index=True)
    children_ids = fields.One2many('account.analytic.group', 'parent_id', string="Childrens")
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for group in self:
            if group.parent_id:
                group.complete_name = '%s / %s' % (group.parent_id.complete_name, group.name)
            else:
                group.complete_name = group.name

class AccountAnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'code, name asc'
    _check_company_auto = True

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
        if self._context.get('tag_ids'):
            tag_domain = expression.OR([[('tag_ids', 'in', [tag])] for tag in self._context['tag_ids']])
            domain = expression.AND([domain, tag_domain])

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

    name = fields.Char(string='Analytic Account', index=True, required=True, tracking=True)
    code = fields.Char(string='Reference', index=True, tracking=True)
    active = fields.Boolean('Active', help="If the active field is set to False, it will allow you to hide the account without removing it.", default=True)

    group_id = fields.Many2one('account.analytic.group', string='Group', check_company=True)

    line_ids = fields.One2many('account.analytic.line', 'account_id', string="Analytic Lines")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # use auto_join to speed up name_search call
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True, tracking=True, check_company=True)

    balance = fields.Monetary(compute='_compute_debit_credit_balance', string='Balance')
    debit = fields.Monetary(compute='_compute_debit_credit_balance', string='Debit')
    credit = fields.Monetary(compute='_compute_debit_credit_balance', string='Credit')

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
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(AccountAnalyticAccount, self)._name_search(name, args, operator, limit, name_get_uid=name_get_uid)
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            # `partner_id` is in auto_join and the searches using ORs with auto_join fields doesn't work
            # we have to cut the search in two searches ... https://github.com/odoo/odoo/issues/25175
            partner_ids = self.env['res.partner']._search([('name', operator, name)], limit=limit, access_rights_uid=name_get_uid)
            domain = ['|', '|', ('code', operator, name), ('name', operator, name), ('partner_id', 'in', partner_ids)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


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
    product_uom_category_id = fields.Many2one(related='product_uom_id.category_id', readonly=True)
    account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='restrict', index=True, check_company=True)
    partner_id = fields.Many2one('res.partner', string='Partner', check_company=True)
    user_id = fields.Many2one('res.users', string='User', default=_default_user)
    tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_line_tag_rel', 'line_id', 'tag_id', string='Tags', copy=True, check_company=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True, store=True, compute_sudo=True)
    group_id = fields.Many2one('account.analytic.group', related='account_id.group_id', store=True, readonly=True, compute_sudo=True)

    @api.constrains('company_id', 'account_id')
    def _check_company_id(self):
        for line in self:
            if line.account_id.company_id and line.company_id.id != line.account_id.company_id.id:
                raise ValidationError(_('The selected account belongs to another company than the one you\'re trying to create an analytic item for'))
