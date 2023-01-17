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
    def account_get(self, **kwargs):
        domain = self._account_get_build_domain(**kwargs)
        best_index, best_account = -1, self.env['account.analytic.default']
        for account in self.search(domain):
            index = account._account_get_evaluate_index()
            if index > best_index:
                best_index, best_account = index, account
        return best_account

    @api.model
    def _account_get_build_domain(self, **kwargs):
        domain = []
        product_id = kwargs.get('product_id')
        if product_id:
            domain += ['|', ('product_id', '=', product_id)]
        domain += [('product_id', '=', False)]
        partner_id = kwargs.get('partner_id')
        if partner_id:
            domain += ['|', ('partner_id', '=', partner_id)]
        domain += [('partner_id', '=', False)]
        account_id = kwargs.get('account_id')
        if account_id:
            domain += ['|', ('account_id', '=', account_id)]
        domain += [('account_id', '=', False)]
        company_id = kwargs.get('company_id')
        if company_id:
            domain += ['|', ('company_id', '=', company_id)]
        domain += [('company_id', '=', False)]
        user_id = kwargs.get('user_id')
        if user_id:
            domain += ['|', ('user_id', '=', user_id)]
        domain += [('user_id', '=', False)]
        date = kwargs.get('date')
        if date:
            domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
            domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
        return domain

    def _account_get_evaluate_index(self):
        self.ensure_one()
        return sum(
            [
                bool(self.product_id),
                bool(self.partner_id),
                bool(self.account_id),
                bool(self.company_id),
                bool(self.user_id),
                bool(self.date_start),
                bool(self.date_stop),
            ]
        )
