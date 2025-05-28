# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class ProductTemplate(models.Model):
    """Inherited the model for adding new fields and functions"""
    _inherit = 'product.template'

    asset_category_id = fields.Many2one('account.asset.category',
                                        string='Asset Type',
                                        company_dependent=True,
                                        ondelete="restrict")
    deferred_revenue_category_id = fields.Many2one('account.asset.category',
                                                   string='Deferred Revenue Type',
                                                   company_dependent=True,
                                                   ondelete="restrict")

    def _get_asset_accounts(self):
        """Override method to customize asset accounts based on asset and deferred revenue categories."""
        res = super(ProductTemplate, self)._get_asset_accounts()
        if self.asset_category_id:
            res['stock_input'] = self.property_account_expense_id
        if self.deferred_revenue_category_id:
            res['stock_output'] = self.property_account_income_id
        return res
