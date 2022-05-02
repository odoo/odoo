# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticDefault(models.Model):
    _name = "account.analytic.default"
    _description = "Analytic Distribution"
    _rec_name = "analytic_id"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence', help="Gives the sequence order when displaying a list of analytic distribution")
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade', help="Select a product which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)")
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade', help="Select a partner which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this partner, it will automatically take this as an analytic account)")
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', help="Select an accounting account which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this account, it will automatically take this as an analytic account)")
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', help="Select a user which will use analytic account specified in analytic default.")
    company_id = fields.Many2one('res.company', string='Company', ondelete='cascade', help="Select a company which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this company, it will automatically take this as an analytic account)")
    date_start = fields.Date(string='Start Date', help="Default start date for this Analytic Account.")
    date_stop = fields.Date(string='End Date', help="Default end date for this Analytic Account.")

    @api.constrains('analytic_id', 'analytic_tag_ids')
    def _check_account_or_tags(self):
        if any(not default.analytic_id
               and not any(tag.analytic_distribution_ids for tag in default.analytic_tag_ids)
               for default in self
               ):
            raise ValidationError(_('An analytic default requires an analytic account or an analytic tag used for analytic distribution.'))

    @api.model
    def account_get(self, product_id=None, partner_id=None, account_id=None, user_id=None, date=None, company_id=None):
        domain = []
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
        domain += [('product_id', '=', False)]
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
        domain += [('partner_id', '=', False)]
        if account_id:
            domain += ['|', ('account_id', '=', account_id)]
        domain += [('account_id', '=', False)]
        if company_id:
            domain += ['|', ('company_id', '=', company_id)]
        domain += [('company_id', '=', False)]
        if user_id:
            domain += ['|', ('user_id', '=', user_id)]
        domain += [('user_id', '=', False)]
        if date:
            domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
            domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
        best_index = -1
        res = self.env['account.analytic.default']
        for rec in self.search(domain):
            index = 0
            if rec.product_id: index += 1
            if rec.partner_id: index += 1
            if rec.account_id: index += 1
            if rec.company_id: index += 1
            if rec.user_id: index += 1
            if rec.date_start: index += 1
            if rec.date_stop: index += 1
            if index > best_index:
                res = rec
                best_index = index
        return res
