# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestCommon


class StockAccountTestCommon(AccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super(StockAccountTestCommon, cls).setUpClass()

        # Properties: Stock valuation account and journal
        cls.env['ir.property'].create([{
            'name': 'property_stock_valuation_account_id',
            'fields_id': cls.env['ir.model.fields'].search([('model', '=', 'product.category'), ('name', '=', 'property_stock_valuation_account_id')], limit=1).id,
            'value': 'account.account,%s' % (cls.stk.id),
            'company_id': cls.env.company.id,
        }, {
            'name': 'property_stock_valuation_journal',
            'fields_id': cls.env['ir.model.fields'].search([('model', '=', 'product.category'), ('name', '=', 'property_stock_journal')], limit=1).id,
            'value': 'account.journal,%s' % (cls.miscellaneous_journal.id),
            'company_id': cls.env.company.id,
        }])
