# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class account_analytic_tag(models.Model):
    _name = 'account.analytic.tag'
    _description = 'Analytic Tags'
    name = fields.Char(string='Analytic Tag', index=True, required=True)
    color = fields.Integer('Color Index')


class account_analytic_account(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'code, name asc'

    @api.multi
    def _compute_debit_credit_balance(self):
        domain = [('account_id', 'in', self.ids),
                  ('company_id', '=', self.env.user.company_id.id)]
        if self._context.get('from_date', False):
            domain += [('date', '>=', self._context['from_date'])]
        if self._context.get('to_date', False):
            domain += [('date', '<=', self._context['to_date'])]
        # compute debits
        debit_domain = domain + [('amount', '<', 0.0)]
        debits = self.env['account.analytic.line'].read_group(
            debit_domain, ['account_id', 'amount'], ['account_id'])
        debits = {amount['account_id'][0]: amount['amount']
                  for amount in debits}
        # compute credits
        credit_domain = domain + [('amount', '>', 0.0)]
        credits = self.env['account.analytic.line'].read_group(
            credit_domain, ['account_id', 'amount'], ['account_id'])
        credits = {amount['account_id'][0]: amount['amount']
                   for amount in credits}

        for account in self:
            account.credit = credits.get(account.id, 0.0)
            account.debit = abs(debits.get(account.id, 0.0))
            account.balance = account.credit - account.debit

    name = fields.Char(string='Analytic Account', index=True, required=True, track_visibility='onchange')
    code = fields.Char(string='Reference', index=True, track_visibility='onchange')
    # FIXME: we reused account_type to implement the closed accounts (feature removed by mistake on release of v9) without modifying the schemas on already released v9, but it would be more clean to rename it
    account_type = fields.Selection([
        ('normal', 'Active'),
        ('closed', 'Archived')
        ], string='State', required=True, default='normal')

    tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_account_tag_rel', 'account_id', 'tag_id', string='Tags', copy=True)
    line_ids = fields.One2many('account.analytic.line', 'account_id', string="Analytic Lines")

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    # use auto_join to speed up name_search call
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True)

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
            return super(account_analytic_account, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        partners = self.env['res.partner'].search([('name', operator, name)], limit=limit)
        if partners:
            domain = ['|'] + domain + [('partner_id', 'in', partners.ids)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()


class account_analytic_line(models.Model):
    _name = 'account.analytic.line'
    _description = 'Analytic Line'
    _order = 'date desc, id desc'

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    name = fields.Char('Description', required=True)
    date = fields.Date('Date', required=True, index=True, default=fields.Date.context_today)
    amount = fields.Monetary('Amount', required=True, default=0.0)
    unit_amount = fields.Float('Quantity', default=0.0)
    account_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='restrict', index=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='User', default=_default_user)

    tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_line_tag_rel', 'line_id', 'tag_id', string='Tags', copy=True)

    company_id = fields.Many2one(related='account_id.company_id', string='Company', store=True, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
