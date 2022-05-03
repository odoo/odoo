# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields, tests
from odoo.tests.common import Form


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
        self.wh = self.env['stock.warehouse'].create({
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
            'location_dest_id': self.wh.lot_stock_id.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100.0,
            'state': 'done',
            'date': fields.Datetime.now(),
        })
        self.quant1 = self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': self.wh.lot_stock_id.id,
            'quantity': 100.0,
        })
        # ship
        self.move2 = self.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': self.wh.lot_stock_id.id,
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

    def test_report_stock_quantity_stansit(self):
        wh2 = self.env['stock.warehouse'].create({'name': 'WH2', 'code': 'WH2'})
        transit_loc = self.wh.company_id.internal_transit_location_id

        self.move_transit_out = self.env['stock.move'].create({
            'name': 'test_transit_out_1',
            'location_id': self.wh.lot_stock_id.id,
            'location_dest_id': transit_loc.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 25.0,
            'state': 'assigned',
            'date': fields.Datetime.now(),
            'date_deadline': fields.Datetime.now(),
        })
        self.move_transit_in = self.env['stock.move'].create({
            'name': 'test_transit_in_1',
            'location_id': transit_loc.id,
            'location_dest_id': wh2.lot_stock_id.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 25.0,
            'state': 'waiting',
            'date': fields.Datetime.now(),
            'date_deadline': fields.Datetime.now(),
        })

        self.env['base'].flush()
        report = self.env['report.stock.quantity'].read_group(
            [('date', '>=', fields.Date.today()), ('date', '<=', fields.Date.today()), ('product_id', '=', self.product1.id)],
            ['product_qty', 'date', 'product_id', 'state'],
            ['date:day', 'product_id', 'state'],
            lazy=False)

        forecast_in_report = [x['product_qty'] for x in report if x['state'] == 'in']
        self.assertEqual(forecast_in_report, [25])
        forecast_out_report = [x['product_qty'] for x in report if x['state'] == 'out']
        self.assertEqual(forecast_out_report, [-25])

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

    def test_replenishment_report_1(self):
        self.product_replenished = self.env['product.product'].create({
            'name': 'Security razor',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        # get auto-created pull rule from when warehouse is created
        self.wh.reception_route_id.rule_ids.unlink()
        self.env['stock.rule'].create({
            'name': 'Rule Supplier',
            'route_id': self.wh.reception_route_id.id,
            'location_id': self.wh.lot_stock_id.id,
            'location_src_id': self.env.ref('stock.stock_location_suppliers').id,
            'action': 'pull',
            'delay': 1.0,
            'procure_method': 'make_to_stock',
            'picking_type_id': self.wh.in_type_id.id,
        })
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.wh.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': self.ref('stock.picking_type_out'),
        })
        self.env['stock.move'].create({
            'name': 'Delivery',
            'product_id': self.product_replenished.id,
            'product_uom_qty': 500.0,
            'product_uom': self.uom_unit.id,
            'location_id': self.wh.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_id': delivery_picking.id,
        })
        delivery_picking.action_confirm()

        # Trigger the manual orderpoint creation for missing product
        self.env['stock.move'].flush()
        self.env['stock.warehouse.orderpoint'].action_open_orderpoints()

        orderpoint = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', self.product_replenished.id)
        ])
        self.assertTrue(orderpoint)
        self.assertEqual(orderpoint.location_id, self.wh.lot_stock_id)
        self.assertEqual(orderpoint.qty_to_order, 500.0)
        orderpoint.action_replenish()
        self.env['stock.warehouse.orderpoint'].action_open_orderpoints()

        move = self.env['stock.move'].search([
            ('product_id', '=', self.product_replenished.id),
            ('location_dest_id', '=', self.wh.lot_stock_id.id)
        ])
        # Simulate a supplier delay
        move.date = fields.datetime.now() + timedelta(days=1)
        orderpoint = self.env['stock.warehouse.orderpoint'].search([
            ('product_id', '=', self.product_replenished.id)
        ])
        self.assertFalse(orderpoint)

        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = self.product_replenished
        orderpoint_form.location_id = self.wh.lot_stock_id
        orderpoint = orderpoint_form.save()

        self.assertEqual(orderpoint.qty_to_order, 0.0)
        self.env['stock.warehouse.orderpoint'].action_open_orderpoints()
        self.assertEqual(orderpoint.qty_to_order, 0.0)

    def test_inter_warehouse_transfer(self):
        """
        Ensure that the report correctly processes the inter-warehouses SM
        """
        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'type': 'product',
        })

        today = datetime.now()
        two_days_ago = today - timedelta(days=2)
        in_two_days = today + timedelta(days=2)

        wh01, wh02 = self.env['stock.warehouse'].create([{
            'name': 'Warehouse 01',
            'code': 'WH01',
        }, {
            'name': 'Warehouse 02',
            'code': 'WH02',
        }])

        self.env['stock.quant']._update_available_quantity(product, wh01.lot_stock_id, 3, in_date=two_days_ago)

        # Let's have 2 inter-warehouses stock moves (one for today and one for two days from now)
        move01, move02 = self.env['stock.move'].create([{
            'name': 'Inter WH Move',
            'location_id': wh01.lot_stock_id.id,
            'location_dest_id': wh02.lot_stock_id.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1,
            'date': date,
        } for date in (today, in_two_days)])

        (move01 + move02)._action_confirm()
        move01.quantity_done = 1
        move01._action_done()

        self.env['stock.move'].flush()

        data = self.env['report.stock.quantity'].read_group(
            [('state', '=', 'forecast'), ('product_id', '=', product.id), ('date', '>=', two_days_ago), ('date', '<=', in_two_days)],
            ['product_qty', 'date', 'warehouse_id'],
            ['date:day', 'warehouse_id'],
            orderby='date, warehouse_id',
            lazy=False,
        )

        for row, qty in zip(data, [
            # wh01_qty, wh02_qty
            3.0, 0.0,   # two days ago
            3.0, 0.0,
            2.0, 1.0,   # today
            2.0, 1.0,
            1.0, 2.0,   # in two days
        ]):
            self.assertEqual(row['product_qty'], qty, "Incorrect qty for Date '%s' Warehouse '%s'" % (row['date:day'], row['warehouse_id'][1]))
