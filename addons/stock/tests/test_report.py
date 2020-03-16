# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo.tests.common import Form, TransactionCase


class TestReports(TransactionCase):
    def test_reports(self):
        product1 = self.env['product.product'].create({
            'name': 'Mellohi',
            'default_code': 'C418',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'tracking': 'lot',
            'barcode': 'scan_me'
        })
        lot1 = self.env['stock.production.lot'].create({
            'name': 'Volume-Beta',
            'product_id': product1.id,
            'company_id': self.env.company.id,
        })
        report = self.env.ref('stock.label_lot_template')
        target = b'\n\n\n^XA\n^FO100,50\n^A0N,44,33^FD[C418]Mellohi^FS\n^FO100,100\n^A0N,44,33^FDLN/SN:Volume-Beta^FS\n^FO100,150^BY3\n^BCN,100,Y,N,N\n^FDVolume-Beta^FS\n^XZ\n\n\n'

        rendering, qweb_type = report.render_qweb_text(lot1.id)
        self.assertEqual(target, rendering.replace(b' ', b''), 'The rendering is not good')
        self.assertEqual(qweb_type, 'text', 'the report type is not good')

    def test_report_quantity_1(self):
        product_form = Form(self.env['product.product'])
        product_form.type = 'product'
        product_form.name = 'Product'
        product = product_form.save()

        warehouse = self.env['stock.warehouse'].search([], limit=1)
        stock = self.env['stock.location'].create({
            'name': 'New Stock',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
        })

        # Inventory Adjustement of 50.0 today.
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': stock.id,
            'inventory_quantity': 50
        })
        self.env['stock.move'].flush()
        report_records_today = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty'], [], lazy=False)
        report_records_tomorrow = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today() + timedelta(days=1))],
            ['product_qty'], [])
        report_records_yesterday = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today() - timedelta(days=1))],
            ['product_qty'], [])
        self.assertEqual(sum([r['product_qty'] for r in report_records_today]), 50.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow]), 50.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_yesterday]), 0.0)

        # Delivery of 20.0 units tomorrow
        move_out = self.env['stock.move'].create({
            'name': 'Move Out 20',
            'date_expected': datetime.now() + timedelta(days=1),
            'location_id': stock.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 20.0,
        })
        self.env['stock.move'].flush()
        report_records_tomorrow = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today() + timedelta(days=1))],
            ['product_qty'], [])
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow]), 50.0)
        move_out._action_confirm()
        self.env['stock.move'].flush()
        report_records_tomorrow = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today() + timedelta(days=1))],
            ['product_qty', 'state'], ['state'], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow if r['state'] == 'forecast']), 30.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow if r['state'] == 'out']), -20.0)
        report_records_today = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty', 'state'], ['state'], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records_today if r['state'] == 'forecast']), 50.0)

        # Receipt of 10.0 units tomorrow
        move_in = self.env['stock.move'].create({
            'name': 'Move In 10',
            'date_expected': datetime.now() + timedelta(days=1),
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': stock.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10.0,
        })
        move_in._action_confirm()
        self.env['stock.move'].flush()
        report_records_tomorrow = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today() + timedelta(days=1))],
            ['product_qty', 'state'], ['state'], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow if r['state'] == 'forecast']), 40.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow if r['state'] == 'out']), -20.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow if r['state'] == 'in']), 10.0)
        report_records_today = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty', 'state'], ['state'], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records_today if r['state'] == 'forecast']), 50.0)

        # Delivery of 20.0 units tomorrow
        move_out = self.env['stock.move'].create({
            'name': 'Move Out 30 - Day-1',
            'date_expected': datetime.now() - timedelta(days=1),
            'location_id': stock.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 30.0,
        })
        move_out._action_confirm()
        self.env['stock.move'].flush()
        report_records_today = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty', 'state'], ['state'], lazy=False)
        report_records_tomorrow = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today() + timedelta(days=1))],
            ['product_qty', 'state'], ['state'], lazy=False)
        report_records_yesterday = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today() - timedelta(days=1))],
            ['product_qty', 'state'], ['state'], lazy=False)

        self.assertEqual(sum([r['product_qty'] for r in report_records_yesterday if r['state'] == 'forecast']), -30.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_yesterday if r['state'] == 'out']), -30.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_yesterday if r['state'] == 'in']), 0.0)

        self.assertEqual(sum([r['product_qty'] for r in report_records_today if r['state'] == 'forecast']), 20.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_today if r['state'] == 'out']), 0.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_today if r['state'] == 'in']), 0.0)

        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow if r['state'] == 'forecast']), 10.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow if r['state'] == 'out']), -20.0)
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow if r['state'] == 'in']), 10.0)

    def test_report_quantity_2(self):
        """ Not supported case.
        """
        product_form = Form(self.env['product.product'])
        product_form.type = 'product'
        product_form.name = 'Product'
        product = product_form.save()

        warehouse = self.env['stock.warehouse'].search([], limit=1)
        stock = self.env['stock.location'].create({
            'name': 'Stock Under Warehouse',
            'usage': 'internal',
            'location_id': warehouse.view_location_id.id,
        })
        stock_without_wh = self.env['stock.location'].create({
            'name': 'Stock Outside Warehouse',
            'usage': 'internal',
            'location_id': self.env.ref('stock.stock_location_locations').id,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': stock.id,
            'inventory_quantity': 50
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': stock_without_wh.id,
            'inventory_quantity': 50
        })
        move = self.env['stock.move'].create({
            'name': 'Move outside warehouse',
            'location_id': stock.id,
            'location_dest_id': stock_without_wh.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10.0,
        })
        move._action_confirm()
        self.env['stock.move'].flush()
        report_records = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today()), ('warehouse_id', '!=', False)],
            ['product_qty', 'state'], ['state'], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records if r['state'] == 'forecast']), 40.0)
        report_records = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty', 'state'], ['state'], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records if r['state'] == 'forecast']), 40.0)
        move = self.env['stock.move'].create({
            'name': 'Move outside warehouse',
            'location_id': stock_without_wh.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10.0,
        })
        move._action_confirm()
        self.env['stock.move'].flush()
        report_records = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty', 'state'], ['state'], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records if r['state'] == 'forecast']), 40.0)

    def test_report_quantity_3(self):
        product_form = Form(self.env['product.product'])
        product_form.type = 'product'
        product_form.name = 'Product'
        product = product_form.save()

        warehouse = self.env['stock.warehouse'].search([], limit=1)
        stock = self.env['stock.location'].create({
            'name': 'Rack',
            'usage': 'view',
            'location_id': warehouse.view_location_id.id,
        })
        stock_real_loc = self.env['stock.location'].create({
            'name': 'Drawer',
            'usage': 'internal',
            'location_id': stock.id,
        })

        self.env['stock.move'].flush()
        report_records = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty'], [], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records if r['product_qty']]), 0.0)

        # Receipt of 20.0 units tomorrow
        move_in = self.env['stock.move'].create({
            'name': 'Move In 20',
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': stock.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 20.0,
        })
        move_in._action_confirm()
        move_in.move_line_ids.location_dest_id = stock_real_loc.id
        move_in.move_line_ids.qty_done = 20.0
        move_in._action_done()
        self.env['stock.move'].flush()
        report_records = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty'], [], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records]), 20.0)

        # Delivery of 10.0 units tomorrow
        move_out = self.env['stock.move'].create({
            'name': 'Move Out 10',
            'location_id': stock.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10.0,
        })
        move_out._action_confirm()
        move_out._action_assign()
        move_out.move_line_ids.qty_done = 10.0
        move_out._action_done()
        self.env['stock.move'].flush()
        report_records = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty'], [], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records]), 10.0)
