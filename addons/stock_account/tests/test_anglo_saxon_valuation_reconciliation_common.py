# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.account.tests.account_test_classes import AccountingTestCase

class ValuationReconciliationTestCase(AccountingTestCase):
    """ Base class for tests checking interim accounts reconciliation works
    in anglosaxon accounting. It sets up everything we need in the tests, and is
    extended in both sale_stock and purchase modules to run the 'true' tests.
    """

    def _create_product_category(self): #Done in a separate function to allow override in purchase module
        return self.env['product.category'].create({
            'name': 'Test category',
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
            'property_stock_valuation_account_id': self.valuation_account.id,
            'property_stock_account_input_categ_id': self.input_account.id,
            'property_stock_account_output_categ_id': self.output_account.id,
        })

    def setUp(self):
        super(ValuationReconciliationTestCase, self).setUp()

        self.company = self.env['res.company']._company_default_get()

        self.company.anglo_saxon_accounting = True

        self.currency_one = self.company.currency_id

        currency_two_name = 'USD' if self.currency_one.name != 'USD' else 'EUR'
        self.currency_two = self.env['res.currency'].search([('name', '=', currency_two_name)])

        self.currency_rate = self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 1.234343354, #Totally arbitratry value
        })

        self.input_account = self.env['account.account'].create({
            'name': 'Test stock in',
            'code': 'stock_account_TEST_42',
            'user_type_id': self.env['account.account.type'].search([],limit=1).id,
            'reconcile': True,
            'company_id': self.company.id,
        })

        self.output_account = self.env['account.account'].create({
            'name': 'Test stock out',
            'code': 'stock_account_TEST_43',
            'user_type_id': self.env['account.account.type'].search([],limit=1).id,
            'reconcile': True,
            'company_id': self.company.id,
        })

        self.valuation_account = self.env['account.account'].create({
            'name': 'Test stock valuation',
            'code': 'stock_account_TEST_44',
            'user_type_id': self.env['account.account.type'].search([],limit=1).id,
            'reconcile': True,
            'company_id': self.company.id,
        })

        test_product_category = self._create_product_category()

        uom = self.env['product.uom'].search([], limit=1)
        test_product_delivery_inv_template = self.env['product.template'].create({
            'name': 'Test product template invoiced on delivery',
            'type': 'product',
            'categ_id': test_product_category.id,
            'uom_id': uom.id,
            'uom_po_id': uom.id,
            'invoice_policy': 'delivery',
        })
        test_product_order_inv_template = self.env['product.template'].create({
            'name': 'Test product template invoiced on order',
            'type': 'product',
            'categ_id': test_product_category.id,
            'uom_id': uom.id,
            'uom_po_id': uom.id,
            'invoice_policy': 'delivery',
        })

        self.test_product_order = self.env['product.product'].create({
            'name': 'The chocolate moose - order',
            'product_tmpl_id': test_product_order_inv_template.id,
            'standard_price': 42.0,
        })

        self.test_product_delivery = self.env['product.product'].create({
            'name': 'The chocolate moose - delivery',
            'product_tmpl_id': test_product_delivery_inv_template.id,
            'standard_price': 42.0,
        })

        self.test_partner = self.env['res.partner'].create({
            'name': 'Ruben Rybnik',
            'supplier': True,
            'customer': True,
        })

        self.product_price_unit = 66.0