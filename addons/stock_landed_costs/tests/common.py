# -*- coding: utf-8 -*-

from odoo.addons.account.tests.account_test_classes import AccountingTestCase

class TestStockLandedCostsCommon(AccountingTestCase):

    def setUp(self):
        super(TestStockLandedCostsCommon, self).setUp()
        # Objects
        self.Product = self.env['product.product']
        self.Picking = self.env['stock.picking']
        self.Move = self.env['stock.move']
        self.LandedCost = self.env['stock.landed.cost']
        self.CostLine = self.env['stock.landed.cost.lines']
        # References
        self.supplier_id = self.ref('base.res_partner_2')
        self.customer_id = self.ref('base.res_partner_4')
        self.picking_type_in_id = self.ref('stock.picking_type_in')
        self.picking_type_out_id = self.ref('stock.picking_type_out')
        self.supplier_location_id = self.ref('stock.stock_location_suppliers')
        self.stock_location_id = self.ref('stock.stock_location_stock')
        self.customer_location_id = self.ref('stock.stock_location_customers')
        self.categ_all = self.env.ref('product.product_category_all')
        # Create account
        self.default_account = self.env['account.account'].create({
            'name': "Purchased Stocks",
            'code': "X1101",
            'user_type_id': self.env['account.account.type'].create({
                    'name': 'Expenses',
                    'type': 'other'}).id,
            'reconcile': True})
        self.expenses_journal = self.env['account.journal'].create({
            'name': 'Expenses - Test',
            'code': 'TEXJ',
            'type': 'purchase',
            'default_debit_account_id': self.default_account.id,
            'default_credit_account_id': self.default_account.id})
        # Create product refrigerator & oven
        self.product_refrigerator = self.Product.create({
            'name': 'Refrigerator',
            'type': 'product',
            'cost_method': 'fifo',
            'valuation': 'real_time',
            'standard_price': 1.0,
            'weight': 10,
            'volume': 1,
            'categ_id': self.categ_all.id})
        self.product_oven = self.Product.create({
            'name': 'Microwave Oven',
            'type': 'product',
            'cost_method': 'fifo',
            'valuation': 'real_time',
            'standard_price': 1.0,
            'weight': 20,
            'volume': 1.5,
            'categ_id': self.categ_all.id})
        # Create service type product 1.Labour 2.Brokerage 3.Transportation 4.Packaging
        self.landed_cost = self._create_services('Landed Cost')
        self.brokerage_quantity = self._create_services('Brokerage Cost')
        self.transportation_weight = self._create_services('Transportation Cost')
        self.packaging_volume = self._create_services('Packaging Cost')
        # Ensure the account properties exists.
        self.ensure_account_property('property_stock_account_input')
        self.ensure_account_property('property_stock_account_output')

    def _create_services(self, name):
        return self.Product.create({
            'name': name,
            'landed_cost_ok': True,
            'type': 'service'})
