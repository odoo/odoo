# -*- coding: utf-8 -*-

from odoo import tools
from odoo.addons.account.tests.common import AccountTestCommon
from odoo.modules.module import get_module_resource


class TestStockLandedCostsCommon(AccountTestCommon):

    def setUp(self):
        super(TestStockLandedCostsCommon, self).setUp()
        # Objects
        self.Product = self.env['product.product']
        self.Picking = self.env['stock.picking']
        self.Move = self.env['stock.move']
        self.LandedCost = self.env['stock.landed.cost']
        self.CostLine = self.env['stock.landed.cost.lines']
        # References
        self.supplier_id = self.env['res.partner'].create({'name': 'My Test Supplier'}).id
        self.customer_id = self.env['res.partner'].create({'name': 'My Test Customer'}).id
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
                    'type': 'other',
                    'internal_group': 'liability'}).id,
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
            'standard_price': 1.0,
            'weight': 10,
            'volume': 1,
            'categ_id': self.categ_all.id})
        self.product_refrigerator.categ_id.property_cost_method = 'fifo'
        self.product_refrigerator.categ_id.property_valuation = 'real_time'
        self.product_oven = self.Product.create({
            'name': 'Microwave Oven',
            'type': 'product',
            'standard_price': 1.0,
            'weight': 20,
            'volume': 1.5,
            'categ_id': self.categ_all.id})
        self.product_oven.categ_id.property_cost_method = 'fifo'
        self.product_oven.categ_id.property_valuation = 'real_time'
        # Create service type product 1.Labour 2.Brokerage 3.Transportation 4.Packaging
        self.landed_cost = self._create_services('Landed Cost')
        self.brokerage_quantity = self._create_services('Brokerage Cost')
        self.transportation_weight = self._create_services('Transportation Cost')
        self.packaging_volume = self._create_services('Packaging Cost')

    def _create_services(self, name):
        return self.Product.create({
            'name': name,
            'type': 'service'})
