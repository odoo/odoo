# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account',
        domain=[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card'))],
        help="Used for inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products "
             "into this location, instead of the generic Stock Account set on the product. "
             "This has no effect for internal locations."
             "In real-time: The product's account will be used as counterparty account."
             "During closing: The company's stock valuation account will be used as counterparty account.")
    is_valued_internal = fields.Boolean('Is valued inside the company', compute="_compute_is_valued")
    is_valued_external = fields.Boolean('Is valued outside the company', compute="_compute_is_valued")

    def _compute_is_valued(self):
        for location in self:
            if location._should_be_valued():
                location.is_valued_internal = True
                location.is_valued_external = False
            else:
                location.is_valued_internal = False
                location.is_valued_external = True

    def _should_be_valued(self):
        """ This method returns a boolean reflecting whether the products stored in `self` should
        be considered when valuating the stock of a company.
        """
        self.ensure_one()
        return bool(self.company_id) and self.usage in ['internal', 'transit']
