# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, tests


class TestReportStockQuantity(tests.TransactionCase):
    def setUp(self):
        super().setUp()
        self.product1 = self.env['product.product'].create({
            'name': 'Mellohi',
            'default_code': 'C418',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'tracking': 'lot',
            'barcode': 'scan_me'
        })
        wh = self.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'code': 'TESTWH'
        })
        self.categ_unit = self.env.ref('uom.product_uom_categ_unit')
        self.uom_unit = self.env['uom.uom'].search([('category_id', '=', self.categ_unit.id), ('uom_type', '=', 'reference')], limit=1)
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        # replenish
        self.move1 = self.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': wh.lot_stock_id.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
            'state': 'done',
            'date': fields.Datetime.now(),
        })
        self.quant1 = self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': wh.lot_stock_id.id,
            'quantity': 100.0,
        })
        # ship
        self.move2 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': wh.lot_stock_id.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 120.0,
            'state': 'partially_available',
            'date': fields.Datetime.add(fields.Datetime.now(), days=3),
            'date_deadline': fields.Datetime.add(fields.Datetime.now(), days=3),
        })
        self.env['base'].flush()

    def test_report_stock_quantity(self):
        from_date = fields.Date.to_string(fields.Date.add(fields.Date.today(), days=-1))
        to_date = fields.Date.to_string(fields.Date.add(fields.Date.today(), days=4))
        report = self.env['report.stock.quantity'].read_group(
            [('date', '>=', from_date), ('date', '<=', to_date), ('product_id', '=', self.product1.id)],
            ['product_qty', 'date', 'product_id', 'state'],
            ['date:day', 'product_id', 'state'],
            lazy=False)
        forecast_report = [x['product_qty'] for x in report if x['state'] == 'forecast']
        self.assertEqual(forecast_report, [0, 100, 100, 100, -20, -20])

    def test_report_stock_quantity_with_product_qty_filter(self):
        from_date = fields.Date.to_string(fields.Date.add(fields.Date.today(), days=-1))
        to_date = fields.Date.to_string(fields.Date.add(fields.Date.today(), days=4))
        report = self.env['report.stock.quantity'].read_group(
            [('product_qty', '<', 0), ('date', '>=', from_date), ('date', '<=', to_date), ('product_id', '=', self.product1.id)],
            ['product_qty', 'date', 'product_id', 'state'],
            ['date:day', 'product_id', 'state'],
            lazy=False)
        forecast_report = [x['product_qty'] for x in report if x['state'] == 'forecast']
        self.assertEqual(forecast_report, [-20, -20])
