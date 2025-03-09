# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form


class TestComputeAveragePriceMultiCompany(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.CompanyA = cls.env['res.company'].create({'name': 'Company A'})
        cls.CompanyB = cls.env['res.company'].create({'name': 'Company B'})

        cls.Product = cls.env['product.product']
        cls.Bom = cls.env['mrp.bom']
        cls.StockMove = cls.env['stock.move']

        # Main Product
        cls.main_product = cls.Product.create({
            'name': '[MAX.CSS100] MAX.CSS wheel chock system with cable reel in wheel guide',
            'type': 'product', 
            'standard_price': 2237.84, 
            'company_id': cls.CompanyB.id,
        })

        # Create products
        cls.product_b = cls.Product.with_company(cls.CompanyB).create({
            'name': 'Product B',
            'type': 'product',
            'standard_price': 100,
            'company_id': cls.CompanyB.id,
        })

        cls.product_c = cls.Product.with_company(cls.CompanyB).create({
            'name': 'Product C',
            'type': 'product',
            'standard_price': 80,
            'company_id': cls.CompanyB.id,
        })

        cls.product_d = cls.Product.with_company(cls.CompanyB).create({
            'name': 'Product D',
            'type': 'product',
            'standard_price': 60,
            'company_id': cls.CompanyB.id,
        })

        # Create BoM for main product
        cls.bom_b = cls.Bom.with_company(cls.CompanyB).create({
            'product_id': cls.main_product.id,
            'product_tmpl_id': cls.main_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_b.id, 'product_qty': 5}),
                (0, 0, {'product_id': cls.product_c.id, 'product_qty': 3}),
                (0, 0, {'product_id': cls.product_d.id, 'product_qty': 3}),
            ]
        })

        # Create stock moves and explicitly set bom_line_id
        cls.stock_moves = cls.StockMove.create([
            {
                'name': '[MAX.CSS100] Système cale-roue MAX.CSS',
                'product_id': cls.main_product.id,
                'product_uom_qty': 1.0,
                'product_uom': 1, 
                'state': 'assigned',
                'company_id': cls.CompanyB.id, 
                'location_id': cls.env.ref('stock.stock_location_stock').id,
                'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
            },
            {
                'name': 'Move 1',
                'product_id': cls.product_b.id,
                'company_id': cls.CompanyB.id,
                'product_uom_qty': 5,
                'product_uom': cls.product_b.uom_id.id,
                'bom_line_id': cls.bom_b.bom_line_ids[0].id,
                'location_id': cls.env.ref('stock.stock_location_stock').id,
                'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
                'state': 'done',
            },
            {
                'name': 'Move 2',
                'product_id': cls.product_c.id,
                'company_id': cls.CompanyB.id,
                'product_uom_qty': 3,
                'product_uom': cls.product_c.uom_id.id,
                'bom_line_id': cls.bom_b.bom_line_ids[1].id,
                'location_id': cls.env.ref('stock.stock_location_stock').id,
                'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
                'state': 'done',
            },
            {
                'name': 'Move 3',
                'product_id': cls.product_d.id,
                'company_id': cls.CompanyB.id,
                'product_uom_qty': 3,
                'product_uom': cls.product_d.uom_id.id,
                'bom_line_id': cls.bom_b.bom_line_ids[1].id,
                'location_id': cls.env.ref('stock.stock_location_stock').id,
                'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
                'state': 'done',
            },
        ])


    def test_compute_average_price_with_multiple_products(self):
        """Ensure _compute_average_price correctly considers multiple stock moves and BoMs"""

        # Ensure we're in Company A's context
        self.env.company = self.CompanyA

        # Compute average price
        computed_price = self.main_product.with_company(self.CompanyB)._compute_average_price(
            qty_invoiced=0,
            qty_to_invoice=1,
            stock_moves=self.stock_moves,
            is_returned=False
        )

        # Assertions
        self.assertNotEqual(computed_price, 0, "Computed price should not be 0")
