# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, exceptions


class AccountAnalyticDistribution(models.Model):
    _name = 'account.analytic.distribution'
    account_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=True)
    percentage = fields.Float(string='Percentage', required=True, default=100.0)
    name = fields.Char(string='Name', related='account_id.name')
    tag_id = fields.Many2one('account.analytic.tag', string="Parent tag")

    @api.onchange('percentage')
    def _onchange_percentage(self):
        if self.percentage > 100:
            return {'warning': {
                    'title' : "Invalid percentage",
                    'message': "The percentage cannot be greater than 100%"
                }
            }
        if self.percentage < 0:
            return {'warning': {
                    'title' : "Invalid percentage",
                    'message': "The percentage cannot be less than 0%"
                }
            }

class AccountAnalyticTag(models.Model):
    _name = 'account.analytic.tag'
    _description = 'Analytic Tags'
    name = fields.Char(string='Analytic Tag', index=True, required=True)
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True, help="Set active to false to hide the Analytic Tag without removing it.")
    analytic_distribution = fields.Boolean(string="Analytic Distribution")
    analytic_distribution_ids = fields.One2many('account.analytic.distribution', 'tag_id', string="Analytic Accounts")

    @api.constrains('analytic_distribution_ids')
    def _check_analytic_distribution(self):
        total_percentage = 0
        negative_percentage = False
        for r in self.analytic_distribution_ids:
            total_percentage = total_percentage + r.percentage

            if r.percentage < 0:
                negative_percentage = True

        if total_percentage > 100.0:
            raise exceptions.ValidationError("The total sum of percentages cannot be greater than 100%")

        if negative_percentage == True:
            raise exceptions.ValidationError("There cannot be a negative percentage.")




class AccountAnalyticCategory(models.Model):
    _name = 'account.analytic.category'
    _description = 'Analytic Categories'
    name = fields.Char(string='Category', required=True)
    description = fields.Text(string='Description')
    parent_id = fields.Many2one('account.analytic.category', string="Parent")
    children_ids = fields.One2many('account.analytic.category', 'parent_id', string="Childrens")

class AccountAnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'code, name asc'

    @api.multi
    def _compute_debit_credit_balance(self):
        analytic_line_obj = self.env['account.analytic.line']
        domain = [('account_id', 'in', self.mapped('id'))]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        account_amounts = analytic_line_obj.search_read(domain, ['account_id', 'amount'])
        account_ids = set([line['account_id'][0] for line in account_amounts])
        data_debit = {account_id: 0.0 for account_id in account_ids}
        data_credit = {account_id: 0.0 for account_id in account_ids}
        for account_amount in account_amounts:
            if account_amount['amount'] < 0.0:
                data_debit[account_amount['account_id'][0]] += account_amount['amount']
            else:
                data_credit[account_amount['account_id'][0]] += account_amount['amount']

        for account in self:
            account.debit = abs(data_debit.get(account.id, 0.0))
            account.credit = data_credit.get(account.id, 0.0)
            account.balance = account.credit - account.debit

    name = fields.Char(string='Analytic Account', index=True, required=True, track_visibility='onchange')
    code = fields.Char(string='Reference', index=True, track_visibility='onchange')
    active = fields.Boolean('Active', help="If the active field is set to False, it will allow you to hide the account without removing it.", default=True)

    tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_account_tag_rel', 'account_id', 'tag_id', string='Tags', copy=True)
    category_id = fields.Many2one('account.analytic.category', string="Category")

    line_ids = fields.One2many('account.analytic.line', 'account_id', string="Analytic Lines")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    # use auto_join to speed up name_search call
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True, track_visibility='onchange')

    balance = fields.Monetary(compute='_compute_debit_credit_balance', string='Balance')
    debit = fields.Monetary(compute='_compute_debit_credit_balance', string='Debit')
    credit = fields.Monetary(compute='_compute_debit_credit_balance', string='Credit')

    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)

    @api.multi
    def name_get(self):
        res = []
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name = '['+analytic.code+'] '+name
            if analytic.partner_id:
                name = name +' - '+analytic.partner_id.commercial_partner_id.name
            res.append((analytic.id, name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(AccountAnalyticAccount, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        partners = self.env['res.partner'].search([('name', operator, name)], limit=limit)
        if partners:
            domain = ['|'] + domain + [('partner_id', 'in', partners.ids)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()


class AccountAnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc, id desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)



    def _compute_amount_user_currency(self):
        """ Compute the amount into the user's currency
        """
        context = dict(self._context or {})
        user_currency_id = self.env.user.company_id.currency_id
        ctx = context.copy()
        for line in self:
            ctx['date'] = line.date
            company_currency_id = line.company_id.currency_id
            amount = line.amount
            if user_currency_id == company_currency_id:
                line.amount_user_currency = amount
            else:
                line.amount_user_currency = company_currency_id.with_context(ctx).compute(amount, user_currency_id)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(AccountAnalyticLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        # We compute the amount that have to be displayed into the user's currency
        # We must call '_compute_amount_user_currency' manually, because of the pivot view not doing it.
        if 'amount_user_currency' in fields:
            self._compute_amount_user_currency()
            for line in res:
                __domain = list('__domain' in line and line['__domain'] or [])
                records = self.search_read(__domain, ['amount_user_currency'])
                line['amount_user_currency'] = 0
                for r in records:
                    line['amount_user_currency'] = line['amount_user_currency'] + r['amount_user_currency']
        return res




    name = fields.Char('Description', required=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    amount = fields.Monetary('Amount', required=True, default=0.0)
    unit_amount = fields.Float('Quantity', default=0.0)
    account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='restrict', index=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='User', default=_default_user)

    tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_line_tag_rel', 'line_id', 'tag_id', string='Tags', copy=True)

    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
    amount_user_currency = fields.Monetary(compute='_compute_amount_user_currency', string='Amount User Currency', help='Amount expressed in the user currency.')
