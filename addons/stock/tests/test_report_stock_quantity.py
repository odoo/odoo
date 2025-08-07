# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields, tests
from odoo.fields import Command
from odoo.tests import Form
from freezegun import freeze_time


class TestReportStockQuantity(tests.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # freeze time to avoid test errors due to the class being initialized before 00:00:00 and the test run after
        cls.fake_today = fields.Date.today()
        cls.startClassPatcher(freeze_time(cls.fake_today))
        cls.product1 = cls.env['product.product'].create({
            'name': 'Mellohi',
            'default_code': 'C418',
            'is_storable': True,
            'tracking': 'lot',
            'barcode': 'scan_me'
        })
        cls.wh = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'code': 'TESTWH'
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        # replenish
        cls.move1 = cls.env['stock.move'].create({
            'name': 'test_in_1',
            'location_id': cls.supplier_location.id,
            'location_dest_id': cls.wh.lot_stock_id.id,
            'product_id': cls.product1.id,
            'product_uom': cls.uom_unit.id,
            'product_uom_qty': 100.0,
            'quantity': 100.0,
            'state': 'done',
            'date': fields.Datetime.now(),
        })
        # ship
        cls.move2 = cls.env['stock.move'].create({
            'name': 'test_out_1',
            'location_id': cls.wh.lot_stock_id.id,
            'location_dest_id': cls.customer_location.id,
            'product_id': cls.product1.id,
            'product_uom': cls.uom_unit.id,
            'product_uom_qty': 120.0,
            'state': 'partially_available',
            'date': fields.Datetime.add(fields.Datetime.now(), days=3),
            'date_deadline': fields.Datetime.add(fields.Datetime.now(), days=3),
        })

    def test_report_stock_quantity(self):
        from_date = fields.Date.to_string(fields.Date.add(fields.Date.today(), days=-1))
        to_date = fields.Date.to_string(fields.Date.add(fields.Date.today(), days=4))
        report = self.env['report.stock.quantity']._read_group(
            [('date', '>=', from_date), ('date', '<=', to_date), ('product_id', '=', self.product1.id)],
            ['date:day', 'product_id', 'state'],
            ['product_qty:sum'])
        forecast_report = [qty for __, __, state, qty in report if state == 'forecast']
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

        self.env.flush_all()
        report = self.env['report.stock.quantity']._read_group(
            [('date', '>=', fields.Date.today()), ('date', '<=', fields.Date.today()), ('product_id', '=', self.product1.id)],
            ['date:day', 'product_id', 'state'],
            ['product_qty:sum'])

        forecast_in_report = [qty for __, __, state, qty in report if state == 'in']
        self.assertEqual(forecast_in_report, [25])
        forecast_out_report = [qty for __, __, state, qty in report if state == 'out']
        self.assertEqual(forecast_out_report, [-25])

    def test_report_stock_quantity_with_product_qty_filter(self):
        from_date = fields.Date.to_string(fields.Date.add(fields.Date.today(), days=-1))
        to_date = fields.Date.to_string(fields.Date.add(fields.Date.today(), days=4))
        report = self.env['report.stock.quantity']._read_group(
            [('product_qty', '<', 0), ('date', '>=', from_date), ('date', '<=', to_date), ('product_id', '=', self.product1.id)],
            ['date:day', 'product_id', 'state'],
            ['product_qty:sum'])
        forecast_report = [qty for __, __, state, qty in report if state == 'forecast']
        self.assertEqual(forecast_report, [-20, -20])

    def test_replenishment_report_1(self):
        self.product_replenished = self.env['product.product'].create({
            'name': 'Security razor',
            'is_storable': True,
        })
        # get auto-created pull rule from when warehouse is created
        self.wh.reception_route_id.rule_ids.unlink()
        self.env['stock.rule'].create({
            'name': 'Rule Supplier',
            'route_id': self.wh.reception_route_id.id,
            'location_dest_id': self.wh.lot_stock_id.id,
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
        self.env.flush_all()
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
        move.date = fields.Datetime.now() + timedelta(days=1)
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
            'is_storable': True,
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
        move01.quantity = 1
        move01.picked = True
        move01._action_done()

        self.env.flush_all()

        data = self.env['report.stock.quantity']._read_group(
            [('state', '=', 'forecast'), ('product_id', '=', product.id), ('date', '>=', two_days_ago), ('date', '<=', in_two_days)],
            ['date:day', 'warehouse_id'],
            ['product_qty:sum'],
        )

        for (date_day, warehouse, qty_rd), qty in zip(data, [
            # wh01_qty, wh02_qty
            3.0, 0.0,   # two days ago
            3.0, 0.0,
            2.0, 1.0,   # today
            2.0, 1.0,
            1.0, 2.0,   # in two days
        ]):
            self.assertEqual(qty_rd, qty, f"Incorrect qty for Date '{date_day}' Warehouse '{warehouse.display_name}'")

    def test_past_date_quantity_with_multistep_delivery(self):
        """
        Verify that available quantities are correctly computed at different past dates
        when using multi-step reciept/delivery.
        """
        def get_inv_qty_at_date(product_id, inv_datetime):
            inventory_at_date_wizard = self.env['stock.quantity.history'].create({'inventory_datetime': inv_datetime})
            r = inventory_at_date_wizard.open_at_date()
            return next((product['qty_available'], product['virtual_available']) for product in self.env[r['res_model']].with_context(r['context']).search_read(
                    domain=(r['domain'] + [('id', '=', product_id)]),
                    fields=['qty_available', 'virtual_available']
                ))
        # We add a second warehouse and put the resuplying flow in push mechanic to test receipt in 2 steps with an external transfer
        warehouse, warehouse_2 = self.wh, self.env['stock.warehouse'].create({
            'name': 'Resupplier warehouse',
            'code': 'WH02',
        })
        transit_loc = self.wh.company_id.internal_transit_location_id
        warehouse.write({
            'resupply_wh_ids': [Command.set(warehouse_2.ids)],
            'delivery_steps': 'pick_ship',
        })
        warehouse.resupply_route_ids.rule_ids.filtered(lambda r: r.location_src_id == transit_loc).action = 'push'
        product = self.env['product.product'].create({'name': 'Test', 'is_storable': True})
        today = fields.Date.today()
        with freeze_time(today - timedelta(days=8)):
            move_transit = self.env['stock.move'].create({
                'name': 'test transit',
                'warehouse_id': warehouse.id,
                'picking_type_id': warehouse.in_type_id.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': transit_loc.id,
                'location_final_id': warehouse.lot_stock_id.id,
                'route_ids': [Command.set(warehouse.resupply_route_ids.ids)],
                'product_id': product.id,
                'product_uom_qty': 150.0,
            })
            move_transit._action_confirm()
            move_transit.write({'quantity': 150.0, 'picked': True})
            move_transit._action_done()
            self.assertRecordValues(product.with_context(warehouse_id=warehouse.id), [{'qty_available': 0.0, 'virtual_available': 150.0}])
            move_transit._action_done()
            self.assertRecordValues(product.with_context(warehouse_id=warehouse.id), [{'qty_available': 0.0, 'virtual_available': 150.0}])

        with freeze_time(today - timedelta(days=6)):
            move_in = move_transit.move_dest_ids
            move_in._action_confirm()
            move_in.write({'quantity': 100.0, 'picked': True})
            self.assertRecordValues(product.with_context(warehouse_id=warehouse.id), [{'qty_available': 0.0, 'virtual_available': 150.0}])
            move_in._action_done()
            self.assertRecordValues(product.with_context(warehouse_id=warehouse.id), [{'qty_available': 100.0, 'virtual_available': 150.0}])

        with freeze_time(today - timedelta(days=4)):
            move_pick = self.env['stock.move'].create({
                'name': 'pick',
                'picking_type_id': warehouse.pick_type_id.id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.wh_output_stock_loc_id.id,
                'location_final_id': self.customer_location.id,
                'product_id': product.id,
                'product_uom_qty': 60.0,
            })
            move_pick._action_confirm()
            self.assertRecordValues(product.with_context(warehouse_id=warehouse.id), [{'qty_available': 100.0, 'virtual_available': 90.0}])
            move_pick.write({'quantity': 60.0, 'picked': True})
            move_pick._action_done()
            self.assertRecordValues(product.with_context(warehouse_id=warehouse.id), [{'qty_available': 100.0, 'virtual_available': 90.0}])

        with freeze_time(today - timedelta(days=2)):
            move_out = move_pick.move_dest_ids
            move_out.write({'quantity': 25.0, 'picked': True})
            self.assertRecordValues(product.with_context(warehouse_id=warehouse.id), [{'qty_available': 100.0, 'virtual_available': 90.0}])
            move_out._action_done()
            self.assertRecordValues(product.with_context(warehouse_id=warehouse.id), [{'qty_available': 75.0, 'virtual_available': 90.0}])

        for date, expected_qties in (
            (move_transit.date - timedelta(days=1), (0.0, 0.0)),
            (move_in.date - timedelta(days=1), (0.0, 50.0)),  # The backorder of move_in contributes in the incoming qty
            (move_pick.date - timedelta(days=1), (100.0, 150.0)),
            (move_out.date - timedelta(days=1), (100.0, 115.0)),  # The backorder of move_out contributes in the outgoing qty
            (today - timedelta(days=1), (75.0, 90.0)),
        ):
            qty = get_inv_qty_at_date(product.id, date)
            self.assertEqual(qty, expected_qties)
