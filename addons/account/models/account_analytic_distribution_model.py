# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    account_prefix = fields.Char(
        string='Accounts Prefix',
        help="This analytic distribution will apply to all financial accounts sharing the prefix specified.",
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        ondelete='cascade',
        check_company=True,
        help="Select a product for which the analytic distribution will be used (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)",
    )
    product_categ_id = fields.Many2one(
        'product.category',
        string='Product Category',
        ondelete='cascade',
        help="Select a product category which will use analytic account specified in analytic default (e.g. create new customer invoice or Sales order if we select this product, it will automatically take this as an analytic account)",
    )

    def _get_default_search_domain_vals(self):
        return super()._get_default_search_domain_vals() | {
            'product_id': False,
            'product_categ_id': False,
        }

    def _get_applicable_models(self, vals):
        applicable_models = super()._get_applicable_models(vals)
        return applicable_models.filtered(lambda m:
            not m.account_prefix or vals.get('account_prefix', '').startswith(m.account_prefix)
        )

    def _create_domain(self, fname, value):
        if fname == 'account_prefix':
            return []
        return super()._create_domain(fname, value)
