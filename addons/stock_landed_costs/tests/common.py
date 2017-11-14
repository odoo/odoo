# -*- coding: utf-8 -*-

from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestStockLandedCostsCommon(AccountingTestCase):

    def setUp(self):
        super(TestStockLandedCostsCommon, self).setUp()
        # Objects
        self.Product = self.env['product.product']
        self.ProductUom = self.env['product.uom']
        self.Picking = self.env['stock.picking']
        self.Move = self.env['stock.move']
        self.LandedCost = self.env['stock.landed.cost']
        self.CostLine = self.env['stock.landed.cost.lines']

        # References
        self.supplier_id = self.ref('base.res_partner_2')
        self.customer_id = self.ref('base.res_partner_4')
        # Picking Types
        self.picking_type_in_id = self.ref('stock.picking_type_in')
        self.picking_type_out_id = self.ref('stock.picking_type_out')
        # Locations
        self.supplier_location_id = self.ref('stock.stock_location_suppliers')
        self.stock_location_id = self.ref('stock.stock_location_stock')
        self.customer_location_id = self.ref('stock.stock_location_customers')
        # Unit of Measure
        self.uom_unit_id = self.ref('product.product_uom_unit')
        self.uom_dozen_id = self.ref('product.product_uom_dozen')
        # Category
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
        self.product_refrigerator = self._create_product('Refrigerator', uom_id=self.uom_unit_id, weight=10.0, volume=1.0)
        self.product_oven = self._create_product('Microwave Oven', uom_id=self.uom_unit_id, weight=20.0, volume=1.5)
        # Create service type product 1.Labour 2.Brokerage 3.Transportation 4.Packaging
        self.product_uom_categ_unit = self.ref('product.product_uom_categ_unit')
        # Define undivisible units
        self.product_uom_unit_round_1 = self.ProductUom.create({
            'category_id': self.product_uom_categ_unit,
            'name': "Uom Unit",
            'factor': 1.0,
            'rounding': 1.0})
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

    def _create_product(self, name, uom_id, weight=0.0, volume=0.0):
        product = self.Product.create({
            'name': name,
            'type': 'product',
            'cost_method': 'fifo',
            'valuation': 'real_time',
            'uom_id': uom_id,
            'standard_price': 1.0,
            'weight': weight,
            'volume': volume,
            'categ_id': self.categ_all.id})
        return product

    def _create_shipment(self, product, uom_id, picking_type_id, location_src_id, location_dest_id, qty, price=1.0):
        return self.Picking.create({
            'name': 'Picking %s' % product.name,
            'picking_type_id': picking_type_id,
            'location_id': location_src_id,
            'location_dest_id': location_dest_id,
            'move_lines': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': price,
                'product_uom':  uom_id,
                'location_id': location_src_id,
                'location_dest_id': location_dest_id,
                })]
            })

    def _error_message(self, actual_cost, computed_cost):
        return 'Additional Landed Cost should be %s instead of %s' % (actual_cost, computed_cost)
