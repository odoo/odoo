# -*- coding: utf-8 -*-

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon


class TestStockLandedCostsCommon(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Objects
        cls.Product = cls.env['product.product']
        cls.Picking = cls.env['stock.picking']
        cls.Move = cls.env['stock.move']
        cls.LandedCost = cls.env['stock.landed.cost']
        cls.CostLine = cls.env['stock.landed.cost.lines']
        # References
        cls.warehouse = cls.company_data['default_warehouse']
        cls.supplier_id = cls.env['res.partner'].create({'name': 'My Test Supplier'}).id
        cls.customer_id = cls.env['res.partner'].create({'name': 'My Test Customer'}).id
        cls.supplier_location_id = cls.env.ref('stock.stock_location_suppliers').id
        cls.customer_location_id = cls.env.ref('stock.stock_location_customers').id
        cls.categ_all = cls.stock_account_product_categ
        cls.categ_manual_periodic = cls.env.ref('product.product_category_goods').copy({
            "property_valuation": "periodic",
            "property_cost_method": "fifo"
        })
        cls.categ_real_time = cls.env.ref('product.product_category_goods').copy({
            "property_valuation": "real_time",
            "property_cost_method": "average"
        })
        cls.expenses_journal = cls.company_data['default_journal_purchase']
        cls.stock_journal = cls.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        # Create product refrigerator & oven
        cls.product_refrigerator = cls.Product.create({
            'name': 'Refrigerator',
            'is_storable': True,
            'standard_price': 1.0,
            'weight': 10,
            'volume': 1,
            'categ_id': cls.categ_real_time.id})
        cls.product_oven = cls.Product.create({
            'name': 'Microwave Oven',
            'is_storable': True,
            'standard_price': 1.0,
            'weight': 20,
            'volume': 1.5,
            'categ_id': cls.categ_real_time.id})
        # Create service type product 1.Labour 2.Brokerage 3.Transportation 4.Packaging
        cls.landed_cost = cls.Product.create({'name': 'Landed Cost', 'type': 'service', 'categ_id': cls.product_category.id})
        cls.brokerage_quantity = cls.Product.create({'name': 'Brokerage Cost', 'type': 'service', 'categ_id': cls.categ_all.id})
        cls.transportation_weight = cls.Product.create({'name': 'Transportation Cost', 'type': 'service', 'categ_id': cls.categ_all.id})
        cls.packaging_volume = cls.Product.create({'name': 'Packaging Cost', 'type': 'service', 'categ_id': cls.categ_all.id})
