# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestCommon


class StockAccountTestCommon(AccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super(StockAccountTestCommon, cls).setUpClass()

        # Properties: Stock valuation account and journal
        cls.env['ir.property'].set_default(
            'property_stock_valuation_account_id',
            'product.category',
            cls.stk,
            cls.env.company,
        )
        cls.env['ir.property'].set_default(
            'property_stock_journal',
            'product.category',
            cls.miscellaneous_journal,
            cls.env.company,
        )
