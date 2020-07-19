# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestStockLandedCostsCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Objects
        cls.Product = cls.env['product.product']
        cls.Picking = cls.env['stock.picking']
        cls.Move = cls.env['stock.move']
        cls.LandedCost = cls.env['stock.landed.cost']
        cls.CostLine = cls.env['stock.landed.cost.lines']
        # References
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.supplier_id = cls.env['res.partner'].create({'name': 'My Test Supplier'}).id
        cls.customer_id = cls.env['res.partner'].create({'name': 'My Test Customer'}).id
        cls.supplier_location_id = cls.env.ref('stock.stock_location_suppliers').id
        cls.customer_location_id = cls.env.ref('stock.stock_location_customers').id
        cls.categ_all = cls.env.ref('product.product_category_all')
        cls.expenses_journal = cls.company_data['default_journal_purchase']
        # Create product refrigerator & oven
        cls.product_refrigerator = cls.Product.create({
            'name': 'Refrigerator',
            'type': 'product',
            'standard_price': 1.0,
            'weight': 10,
            'volume': 1,
            'categ_id': cls.categ_all.id})
        cls.product_refrigerator.categ_id.property_cost_method = 'fifo'
        cls.product_refrigerator.categ_id.property_valuation = 'real_time'
        cls.product_oven = cls.Product.create({
            'name': 'Microwave Oven',
            'type': 'product',
            'standard_price': 1.0,
            'weight': 20,
            'volume': 1.5,
            'categ_id': cls.categ_all.id})
        cls.product_oven.categ_id.property_cost_method = 'fifo'
        cls.product_oven.categ_id.property_valuation = 'real_time'
        # Create service type product 1.Labour 2.Brokerage 3.Transportation 4.Packaging
        cls.landed_cost = cls.Product.create({'name': 'Landed Cost', 'type': 'service'})
        cls.brokerage_quantity = cls.Product.create({'name': 'Brokerage Cost', 'type': 'service'})
        cls.transportation_weight = cls.Product.create({'name': 'Transportation Cost', 'type': 'service'})
        cls.packaging_volume = cls.Product.create({'name': 'Packaging Cost', 'type': 'service'})
