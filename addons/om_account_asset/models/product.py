# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    asset_category_id = fields.Many2one('account.asset.category', string='Asset Type',
                                        company_dependent=True, ondelete="restrict")
    deferred_revenue_category_id = fields.Many2one('account.asset.category', string='Deferred Revenue Type',
                                                   company_dependent=True, ondelete="restrict")

    def _get_asset_accounts(self):
        res = super(ProductTemplate, self)._get_asset_accounts()
        if self.asset_category_id:
            res['stock_input'] = self.property_account_expense_id
        if self.deferred_revenue_category_id:
            res['stock_output'] = self.property_account_income_id
        return res
