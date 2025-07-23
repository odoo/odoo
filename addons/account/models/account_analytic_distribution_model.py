import re

from odoo import api, fields, models, _


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
    prefix_placeholder = fields.Char(compute='_compute_prefix_placeholder')

    def _get_default_search_domain_vals(self):
        return super()._get_default_search_domain_vals() | {
            'product_id': False,
            'product_categ_id': False,
        }

    def _get_applicable_models(self, vals):
        applicable_models = super()._get_applicable_models(vals)

        # Regex pattern to split by either ';' or ','
        delimiter_pattern = re.compile(r'[;,]\s*')

        return applicable_models.filtered(
            lambda model:
            not model.account_prefix or
            any((vals.get('account_prefix') or '').startswith(prefix) for prefix in delimiter_pattern.split(model.account_prefix))
        )

    def _create_domain(self, fname, value):
        if fname == 'account_prefix':
            return []
        return super()._create_domain(fname, value)

    # To be able to see the placeholder when creating a record in the list view, need to depends on a field that has a
    # value directly, analytic precision has a default.
    @api.depends('analytic_precision')
    def _compute_prefix_placeholder(self):
        expense_account = self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(self.env.company),
            ('account_type', '=', 'expense'),
        ], limit=1)
        for model in self:
            account_prefixes = "60, 61, 62"
            if expense_account:
                prefix_base = expense_account.code[:2]
                try:
                    # Convert prefix_base to an integer for numerical manipulation
                    prefix_num = int(prefix_base)
                    account_prefixes = f"{prefix_num}, {prefix_num + 1}, {prefix_num + 2}"
                except ValueError:
                    pass

            model.prefix_placeholder = _("e.g. %(prefix)s", prefix=account_prefixes)
