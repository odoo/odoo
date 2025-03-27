# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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


# ---------------------------------------------------------
# Account Financial Report
# ---------------------------------------------------------
class AccountTypes(models.Model):
    _name = "account.account.type"
    _description = "Account Types"

    name = fields.Char(string='Account Type', required=True, translate=True)
    type = fields.Selection([
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity', 'Liquidity'),
    ], required=True, default='other',
        help="The 'Internal Type' is used for features available on " \
             "different types of accounts: liquidity type is for cash or bank accounts" \
             ", payable/receivable is for vendor/customer accounts.")


class AccountFinancialReport(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"
    _rec_name = 'name'

    @api.depends('parent_id', 'parent_id.level')
    def _get_level(self):
        """Returns a dictionary with key=the ID of a record and
         value = the level of this
           record in the tree structure."""
        for report in self:
            level = 0
            if report.parent_id:
                level = report.parent_id.level + 1
            report.level = level

    def _get_children_by_order(self):
        """returns a recordset of all the children computed recursively,
         and sorted by sequence. Ready for the printing"""
        res = self
        children = self.search([('parent_id', 'in', self.ids)],
                               order='sequence ASC')
        if children:
            for child in children:
                res += child._get_children_by_order()
        return res

    name = fields.Char('Report Name', required=True, translate=True)
    parent_id = fields.Many2one('account.financial.report', 'Parent')
    children_ids = fields.One2many(
        'account.financial.report',
        'parent_id',
        'Account Report')
    sequence = fields.Integer('Sequence')
    level = fields.Integer(compute='_get_level', string='Level', store=True, recursive=True)
    type = fields.Selection(
        [('sum', 'View'),
         ('accounts', 'Accounts'),
         ('account_type', 'Account Type'),
         ('account_report', 'Report Value')],
        'Type',
        default='sum')
    account_ids = fields.Many2many(
        'account.account',
        'account_account_financial_report',
        'report_line_id',
        'account_id',
        'Accounts')
    account_report_id = fields.Many2one(
        'account.financial.report',
        'Report Value')
    # account_type_ids = fields.Many2many(
    #     'account.account.type',
    #     'Account Types')
    account_type_ids = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type",
        help="These types are defined according to your country. The type contains more information " \
             "about the account and its specificities."
    )
    # account_type_ids = fields.Many2many(
    #     'account.account.template',
    #     'account_account_financial_report_type',
    #     'report_id', 'account_type_id',
    #     'Account Types')

    sign = fields.Selection(
        [("-1", 'Reverse balance sign'), ("1", 'Preserve balance sign')],
        'Sign on Reports', required=True, default="1",
        help='For accounts that are typically more'
             ' debited than credited and that you'
             ' would like to print as negative'
             ' amounts in your reports, you should'
             ' reverse the sign of the balance;'
             ' e.g.: Expense account. The same applies'
             ' for accounts that are typically more'
             ' credited than debited and that you would'
             ' like to print as positive amounts in'
             ' your reports; e.g.: Income account.')
    display_detail = fields.Selection(
        [('no_detail', 'No detail'),
         ('detail_flat', 'Display children flat'),
         ('detail_with_hierarchy', 'Display children with hierarchy')],
        'Display details',
        default='detail_flat')
    style_overwrite = fields.Selection(
        [('0', 'Automatic formatting'),
         ('1', 'Main Title 1 (bold, underlined)'),
         ('2', 'Title 2 (bold)'),
         ('3', 'Title 3 (bold, smaller)'),
         ('4', 'Normal Text'),
         ('5', 'Italic Text (smaller)'),
         ('6', 'Smallest Text')],
        'Financial Report Style',
        default='0',
        help="You can set up here the format you want this"
             " record to be displayed. If you leave the"
             " automatic formatting, it will be computed"
             " based on the financial reports hierarchy "
             "(auto-computed field 'level').")
