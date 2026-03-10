# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import api, fields, models


class AccountAssetCategory(models.Model):
    _name = 'account.asset.category'
    _description = 'Asset category'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True, index=True, string="Asset Type")
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 default=lambda self: self.env.company)
    price = fields.Monetary(string='Price', required=True)
    currency_id = fields.Many2one("res.currency",
                                  default=lambda self: self.env[
                                      'res.currency'].search(
                                      [('name', '=', 'USD')]).id,
                                  readonly=True, hide=True)
    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account',
                                          domain="[('company_id', '=', company_id)]")
    account_asset_id = fields.Many2one('account.account',
                                       string='Asset Account', required=True,
                                       domain="[('account_type', '!=', 'asset_receivable'),('account_type', '!=', 'liability_payable'),('account_type', '!=', 'asset_cash'),('account_type', '!=', 'liability_credit_card'),('active', '=', True)]",
                                       help="Account used to record the purchase of the asset at its original price.")
    account_depreciation_id = fields.Many2one(
        'account.account', string='Depreciation Account',
        required=True,
        domain="[('account_type', '!=', 'asset_receivable'),('account_type', '!=', 'liability_payable'),('account_type', '!=', 'asset_cash'),('account_type', '!=', 'liability_credit_card'),('active', '=', True)]",
        help="Account used in the depreciation entries, to decrease the asset value.")
    account_depreciation_expense_id = fields.Many2one(
        'account.account', string='Expense Account',
        required=True,
        domain="[('account_type', '!=', 'asset_receivable'),('account_type', '!=','liability_payable'),('account_type', '!=', 'asset_cash'),('account_type', '!=','liability_credit_card'),('active', '=', True)]",
        help="Account used in the periodical entries, to record a part of the asset as expense.")
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True)
    method = fields.Selection(
        [('linear', 'Straight Line'), ('degressive', 'Declining')],
        string='Computation Method', required=True, default='linear',
        help="Choose the method to use to compute the amount of depreciation lines.\n"
             "  * Linear: Calculated on basis of: Gross Value / Number of Depreciations\n"
             "  * Degressive: Calculated on basis of: Residual Value * Degressive Factor")
    method_number = fields.Integer(string='Number of Depreciations', default=5,
                                   help="The number of depreciations needed to depreciate your asset")
    method_period = fields.Integer(string='Period Length', default=1,
                                   help="State here the time between 2 depreciations, in months",
                                   required=True)
    method_progress_factor = fields.Float('Degressive Factor', default=0.3)
    method_time = fields.Selection(
        [('number', 'Number of Entries'), ('end', 'Ending Date')],
        string='Time Method', required=True, default='number',
        help="Choose the method to use to compute the dates and number of entries.\n"
             "  * Number of Entries: Fix the number of entries and the time between 2 depreciations.\n"
             "  * Ending Date: Choose the time between 2 depreciations and the date the depreciations won't go beyond.")
    method_end = fields.Date('Ending date')
    prorata = fields.Boolean(string='Prorata Temporis',
                             help='Indicates that the first depreciation entry for this asset have to be done from the purchase date instead of the first of January')
    open_asset = fields.Boolean(string='Auto-confirm Assets',
                                help="Check this if you want to automatically confirm the assets of this category when created by invoices.")
    group_entries = fields.Boolean(string='Group Journal Entries',
                                   help="Check this if you want to group the generated entries by categories.")
    type = fields.Selection([('sale', 'Sale: Revenue Recognition'),
                             ('purchase', 'Purchase: Asset')], required=True,
                            index=True, default='purchase')

    @api.onchange('account_asset_id')
    def onchange_account_asset(self):
        """Onchange method triggered when the 'account_asset_id' field is modified.
            Updates 'account_depreciation_id' or 'account_depreciation_expense_id' based on the 'type' field value."""
        if self.type == "purchase":
            self.account_depreciation_id = self.account_asset_id
        elif self.type == "sale":
            self.account_depreciation_expense_id = self.account_asset_id

    @api.onchange('type')
    def onchange_type(self):
        """Update the 'prorata' and 'method_period' fields based on the value of the 'type' field."""
        if self.type == 'sale':
            self.prorata = True
            self.method_period = 1
        else:
            self.method_period = 12

    @api.onchange('method_time')
    def _onchange_method_time(self):
        """Update the 'prorata' field based on the value of the 'method_time' field.
        Set 'prorata' to False if 'method_time' is not equal to 'number'."""
        if self.method_time != 'number':
            self.prorata = False

    @api.model
    def create(self, vals):
        record = super().create(vals)
        asset_id = self.env.context.get('default_asset_id')
        if asset_id:
            asset = self.env['account.asset.asset'].browse(asset_id)
            asset.category_id = record.id
        return record
