# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountAnalyticApplicability(models.Model):
    _inherit = 'account.analytic.applicability'
    _description = "Analytic Plan's Applicabilities"

    business_domain = fields.Selection(
        selection_add=[
            ('invoice', 'Invoice'),
            ('bill', 'Vendor Bill'),
        ],
        ondelete={
            'invoice': 'cascade',
            'bill': 'cascade',
        },
    )
    account_prefix = fields.Char(
        string='Financial Accounts Prefix',
        help="Prefix that defines which accounts from the financial accounting this applicability should apply on.",
    )
    product_categ_id = fields.Many2one(
        'product.category',
        string='Product Category'
    )
    display_account_prefix = fields.Boolean(
        compute='_compute_display_account_prefix',
        help='Defines if the field account prefix should be displayed'
    )

    def _get_score(self, **kwargs):
        score = super(AccountAnalyticApplicability, self)._get_score(**kwargs)
        if score == -1:
            return -1
        product = self.env['product.product'].browse(kwargs.get('product', None))
        account = self.env['account.account'].browse(kwargs.get('account', None))
        if self.account_prefix:
            if account and account.code.startswith(self.account_prefix):
                score += 1
            else:
                return -1
        if self.product_categ_id:
            if product and product.categ_id == self.product_categ_id:
                score += 1
            else:
                return -1
        return score

    @api.depends('business_domain')
    def _compute_display_account_prefix(self):
        for applicability in self:
            applicability.display_account_prefix = applicability.business_domain in ('general', 'invoice', 'bill')
