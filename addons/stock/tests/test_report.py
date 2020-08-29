# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo.tests.common import Form, SavepointCase


class TestReportsCommon(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Partner'})
        cls.ModelDataObj = cls.env['ir.model.data']
        cls.picking_type_in = cls.env['stock.picking.type'].browse(cls.ModelDataObj.xmlid_to_res_id('stock.picking_type_in'))
        cls.picking_type_out = cls.env['stock.picking.type'].browse(cls.ModelDataObj.xmlid_to_res_id('stock.picking_type_out'))
        cls.supplier_location = cls.env['stock.location'].browse(cls.ModelDataObj.xmlid_to_res_id('stock.stock_location_suppliers'))
        cls.stock_location = cls.env['stock.location'].browse(cls.ModelDataObj.xmlid_to_res_id('stock.stock_location_stock'))

        product_form = Form(cls.env['product.product'])
        product_form.type = 'product'
        product_form.name = 'Product'
        cls.product = product_form.save()
        cls.product_template = cls.product.product_tmpl_id

    def get_report_forecast(self, product_template_ids=False, product_variant_ids=False, context=False):
        if product_template_ids:
            report = self.env['report.stock.report_product_template_replenishment']
            product_ids = product_template_ids
        elif product_variant_ids:
            report = self.env['report.stock.report_product_product_replenishment']
            product_ids = product_template_ids
        if context:
            report = report.with_context(context)
        report_values = report._get_report_values(docids=product_ids)
        docs = report_values['docs']
        lines = docs['lines']
        return report_values, docs, lines


class TestReports(TestReportsCommon):
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

        rendering, qweb_type = report._render_qweb_text(lot1.id)
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
            'date': datetime.now() + timedelta(days=1),
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
            'date': datetime.now() + timedelta(days=1),
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
            'date': datetime.now() - timedelta(days=1),
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

    def test_report_forecast_1(self):
        """ Checks report data for product is empty. Then creates and process
        some operations and checks the report data accords rigthly these operations.
        """
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0, "Must have 0 line.")
        self.assertEqual(draft_picking_qty['in'], 0)
        self.assertEqual(draft_picking_qty['out'], 0)

        # Creates a receipt then checks draft picking quantities.
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt = receipt_form.save()
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 2
        receipt = receipt_form.save()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0, "Must have 0 line.")
        self.assertEqual(draft_picking_qty['in'], 2)
        self.assertEqual(draft_picking_qty['out'], 0)

        # Creates a delivery then checks draft picking quantities.
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery = delivery_form.save()
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery = delivery_form.save()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0, "Must have 0 line.")
        self.assertEqual(draft_picking_qty['in'], 2)
        self.assertEqual(draft_picking_qty['out'], 5)

        # Confirms the delivery: must have one report line and no more pending qty out now.
        delivery.action_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(draft_picking_qty['in'], 2)
        self.assertEqual(draft_picking_qty['out'], 0)
        delivery_line = lines[0]
        self.assertEqual(delivery_line['quantity'], 5)
        self.assertEqual(delivery_line['replenishment_filled'], False)
        self.assertEqual(delivery_line['document_out'].id, delivery.id)

        # Confirms the receipt, must have two report lines now:
        #   - line with 2 qty (from the receipt to the delivery)
        #   - line with 3 qty (delivery, unavailable)
        receipt.action_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 2, "Must have 2 line.")
        self.assertEqual(draft_picking_qty['in'], 0)
        self.assertEqual(draft_picking_qty['out'], 0)
        fulfilled_line = lines[0]
        unavailable_line = lines[1]
        self.assertEqual(fulfilled_line['replenishment_filled'], True)
        self.assertEqual(fulfilled_line['quantity'], 2)
        self.assertEqual(fulfilled_line['document_in'].id, receipt.id)
        self.assertEqual(fulfilled_line['document_out'].id, delivery.id)
        self.assertEqual(unavailable_line['replenishment_filled'], False)
        self.assertEqual(unavailable_line['quantity'], 3)
        self.assertEqual(unavailable_line['document_out'].id, delivery.id)

        # Creates a new receipt for the remaining quantity, confirm it...
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        receipt2 = receipt_form.save()
        receipt2.action_confirm()

        # ... and valid the first one.
        receipt_form = Form(receipt)
        with receipt_form.move_ids_without_package.edit(0) as move_line:
            move_line.quantity_done = 2
        receipt = receipt_form.save()
        receipt.button_validate()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 2, "Still must have 2 line.")
        self.assertEqual(draft_picking_qty['in'], 0)
        self.assertEqual(draft_picking_qty['out'], 0)
        line1 = lines[0]
        line2 = lines[1]
        # First line must be fulfilled thanks to the stock on hand.
        self.assertEqual(line1['quantity'], 2)
        self.assertEqual(line1['replenishment_filled'], True)
        self.assertEqual(line1['document_in'], False)
        self.assertEqual(line1['document_out'].id, delivery.id)
        # Second line must be linked to the second receipt.
        self.assertEqual(line2['quantity'], 3)
        self.assertEqual(line2['replenishment_filled'], True)
        self.assertEqual(line2['document_in'].id, receipt2.id)
        self.assertEqual(line2['document_out'].id, delivery.id)

    def test_report_forecast_2_replenishments_order(self):
        """ Creates a receipt then creates a delivery using half of the receipt quantity.
        Checks replenishment lines are correctly sorted (assigned first, unassigned at the end).
        """
        # Creates a receipt then checks draft picking quantities.
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 6
        receipt = receipt_form.save()
        receipt.action_confirm()

        # Creates a delivery then checks draft picking quantities.
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery = delivery_form.save()
        delivery.action_confirm()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        self.assertEqual(len(lines), 2, "Must have 2 line.")
        line_1 = lines[0]
        line_2 = lines[1]
        self.assertEqual(line_1['document_in'].id, receipt.id)
        self.assertEqual(line_1['document_out'].id, delivery.id)
        self.assertEqual(line_2['document_in'].id, receipt.id)
        self.assertEqual(line_2['document_out'], False)

    def test_report_forecast_3_sort_by_date(self):
        """ Creates some deliveries with different dates and checks the report
        lines are correctly sorted by date. Then, creates some receipts and
        check their are correctly linked according to their date.
        """
        today = datetime.today()
        one_hours = timedelta(hours=1)
        one_day = timedelta(days=1)
        one_month = timedelta(days=30)
        # Creates a bunch of deliveries with different date.
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.scheduled_date = today
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_1 = delivery_form.save()
        delivery_1.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.scheduled_date = today + one_hours
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_2 = delivery_form.save()
        delivery_2.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.scheduled_date = today - one_hours
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_3 = delivery_form.save()
        delivery_3.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.scheduled_date = today + one_day
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_4 = delivery_form.save()
        delivery_4.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.scheduled_date = today - one_day
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_5 = delivery_form.save()
        delivery_5.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.scheduled_date = today + one_month
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_6 = delivery_form.save()
        delivery_6.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.scheduled_date = today - one_month
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery_7 = delivery_form.save()
        delivery_7.action_confirm()

        # Order must be: 7, 5, 3, 1, 2, 4, 6
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 7, "The report must have 7 line.")
        self.assertEqual(draft_picking_qty['in'], 0)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(lines[0]['document_out'].id, delivery_7.id)
        self.assertEqual(lines[1]['document_out'].id, delivery_5.id)
        self.assertEqual(lines[2]['document_out'].id, delivery_3.id)
        self.assertEqual(lines[3]['document_out'].id, delivery_1.id)
        self.assertEqual(lines[4]['document_out'].id, delivery_2.id)
        self.assertEqual(lines[5]['document_out'].id, delivery_4.id)
        self.assertEqual(lines[6]['document_out'].id, delivery_6.id)

        # Creates 3 receipts for 20 units.
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.scheduled_date = today + one_month
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        receipt_1 = receipt_form.save()
        receipt_1.action_confirm()

        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.scheduled_date = today - one_month
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        receipt_2 = receipt_form.save()
        receipt_2.action_confirm()

        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.scheduled_date = today - one_hours
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 10
        receipt_3 = receipt_form.save()
        receipt_3.action_confirm()

        # Check report lines (link and order).
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 7, "The report must have 7 line.")
        self.assertEqual(draft_picking_qty['in'], 0)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(lines[0]['document_out'].id, delivery_7.id)
        self.assertEqual(lines[0]['document_in'].id, receipt_2.id)
        self.assertEqual(lines[0]['is_late'], False)
        self.assertEqual(lines[1]['document_out'].id, delivery_5.id)
        self.assertEqual(lines[1]['document_in'].id, receipt_3.id)
        self.assertEqual(lines[1]['is_late'], True)
        self.assertEqual(lines[2]['document_out'].id, delivery_3.id)
        self.assertEqual(lines[2]['document_in'].id, receipt_3.id)
        self.assertEqual(lines[2]['is_late'], False)
        self.assertEqual(lines[3]['document_out'].id, delivery_1.id)
        self.assertEqual(lines[3]['document_in'].id, receipt_1.id)
        self.assertEqual(lines[3]['is_late'], True)
        self.assertEqual(lines[4]['document_out'].id, delivery_2.id)
        self.assertEqual(lines[4]['document_in'], False)
        self.assertEqual(lines[5]['document_out'].id, delivery_4.id)
        self.assertEqual(lines[5]['document_in'], False)
        self.assertEqual(lines[6]['document_out'].id, delivery_6.id)
        self.assertEqual(lines[6]['document_in'], False)

    def test_report_forecast_4_intermediate_transfers(self):
        """ Create a receipt in 3 steps and check the report line.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_routes = self.env.ref('stock.group_adv_location')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_routes.id)]})
        # Warehouse config.
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.reception_steps = 'three_steps'
        # Product config.
        self.product.write({'route_ids': [(4, self.env.ref('stock.route_warehouse0_mto').id)]})
        # Create a RR
        pg1 = self.env['procurement.group'].create({})
        reordering_rule = self.env['stock.warehouse.orderpoint'].create({
            'name': 'Product RR',
            'location_id': warehouse.lot_stock_id.id,
            'product_id': self.product.id,
            'product_min_qty': 5,
            'product_max_qty': 10,
            'group_id': pg1.id,
        })
        reordering_rule.action_replenish()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        pickings = self.env['stock.picking'].search([('product_id', '=', self.product.id)])
        receipt = pickings.filtered(lambda p: p.picking_type_id.id == self.picking_type_in.id)

        # The Forecasted Report don't show intermediate moves, it must display only ingoing/outgoing documents.
        self.assertEqual(len(lines), 1, "The report must have only 1 line.")
        self.assertEqual(lines[0]['document_in'].id, receipt.id, "The report must only show the receipt.")
        self.assertEqual(lines[0]['document_out'], False)
        self.assertEqual(lines[0]['quantity'], reordering_rule.product_max_qty)

    def test_report_forecast_5_multi_warehouse(self):
        """ Create some transfer for two different warehouses and check the
        report display the good moves according to the selected warehouse.
        """
        # Warehouse config.
        wh_2 = self.env['stock.warehouse'].create({
            'name': 'Evil Twin Warehouse',
            'code': 'ETWH',
        })
        picking_type_out_2 = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('warehouse_id', '=', wh_2.id),
        ])

        # Creates a delivery then checks draft picking quantities.
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery = delivery_form.save()
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        delivery = delivery_form.save()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0, "Must have 0 line.")
        self.assertEqual(draft_picking_qty['out'], 5)

        report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={'warehouse': wh_2.id},
        )
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0)
        self.assertEqual(draft_picking_qty['out'], 0)

        # Confirm the delivery -> The report must now have 1 line.
        delivery.action_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(lines[0]['document_out'].id, delivery.id)
        self.assertEqual(lines[0]['quantity'], 5)

        report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={'warehouse': wh_2.id},
        )
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0)
        self.assertEqual(draft_picking_qty['out'], 0)

        # Creates a delivery for the second warehouse.
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_out_2
        delivery_2 = delivery_form.save()
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 8
        delivery_2 = delivery_form.save()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(lines[0]['document_out'].id, delivery.id)
        self.assertEqual(lines[0]['quantity'], 5)

        report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={'warehouse': wh_2.id},
        )
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0)
        self.assertEqual(draft_picking_qty['out'], 8)
        # Confirm the second delivery -> The report must now have 1 line.
        delivery_2.action_confirm()
        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(lines[0]['document_out'].id, delivery.id)
        self.assertEqual(lines[0]['quantity'], 5)

        report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={'warehouse': wh_2.id},
        )
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 1)
        self.assertEqual(draft_picking_qty['out'], 0)
        self.assertEqual(lines[0]['document_out'].id, delivery_2.id)
        self.assertEqual(lines[0]['quantity'], 8)

    def test_report_forecast_6_multi_company(self):
        """ Create transfers for two different companies and check report
        display the right transfers.
        """
        # Configure second warehouse.
        company_2 = self.env['res.company'].create({'name': 'Aperture Science'})
        wh_2 = self.env['stock.warehouse'].search([('company_id', '=', company_2.id)])
        wh_2_picking_type_in = wh_2.in_type_id

        # Creates a receipt then checks draft picking quantities.
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        wh_1_receipt = receipt_form.save()
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 2
        wh_1_receipt = receipt_form.save()

        # Creates a receipt then checks draft picking quantities.
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = wh_2_picking_type_in
        wh_2_receipt = receipt_form.save()
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        wh_2_receipt = receipt_form.save()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0, "Must have 0 line.")
        self.assertEqual(draft_picking_qty['in'], 2)
        self.assertEqual(draft_picking_qty['out'], 0)

        report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={'warehouse': wh_2.id},
        )
        draft_picking_qty = docs['draft_picking_qty']
        self.assertEqual(len(lines), 0, "Must have 0 line.")
        self.assertEqual(draft_picking_qty['in'], 5)
        self.assertEqual(draft_picking_qty['out'], 0)

        # Confirm the receipts -> The report must now have one line for each company.
        wh_1_receipt.action_confirm()
        wh_2_receipt.action_confirm()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(lines[0]['document_in'].id, wh_1_receipt.id)
        self.assertEqual(lines[0]['quantity'], 2)

        report_values, docs, lines = self.get_report_forecast(
            product_template_ids=self.product_template.ids,
            context={'warehouse': wh_2.id},
        )
        self.assertEqual(len(lines), 1, "Must have 1 line.")
        self.assertEqual(lines[0]['document_in'].id, wh_2_receipt.id)
        self.assertEqual(lines[0]['quantity'], 5)

    def test_report_forecast_7_multiple_variants(self):
        """ Create receipts for different variant products and check the report
        work well with them.Also, check the receipt/delivery lines are correctly
        linked depending of their product variant.
        """
        # Create some variant's attributes.
        product_attr_color = self.env['product.attribute'].create({'name': 'Color'})
        color_gray = self.env['product.attribute.value'].create({
            'name': 'Old Fashioned Gray',
            'attribute_id': product_attr_color.id,
        })
        color_blue = self.env['product.attribute.value'].create({
            'name': 'Electric Blue',
            'attribute_id': product_attr_color.id,
        })
        product_attr_size = self.env['product.attribute'].create({'name': 'size'})
        size_pocket = self.env['product.attribute.value'].create({
            'name': 'Pocket',
            'attribute_id': product_attr_size.id,
        })
        size_xl = self.env['product.attribute.value'].create({
            'name': 'XL',
            'attribute_id': product_attr_size.id,
        })

        # Create a new product and set some variants on the product.
        product_template = self.env['product.template'].create({
            'name': 'Game Joy',
            'type': 'product',
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': product_attr_color.id,
                    'value_ids': [(6, 0, [color_gray.id, color_blue.id])]
                }),
                (0, 0, {
                    'attribute_id': product_attr_size.id,
                    'value_ids': [(6, 0, [size_pocket.id, size_xl.id])]
                }),
            ],
        })
        gamejoy_pocket_gray = product_template.product_variant_ids[0]
        gamejoy_xl_gray = product_template.product_variant_ids[1]
        gamejoy_pocket_blue = product_template.product_variant_ids[2]
        gamejoy_xl_blue = product_template.product_variant_ids[3]

        # Create two receipts.
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = gamejoy_pocket_gray
            move_line.product_uom_qty = 8
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = gamejoy_pocket_blue
            move_line.product_uom_qty = 4
        receipt_1 = receipt_form.save()
        receipt_1.action_confirm()

        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = gamejoy_pocket_gray
            move_line.product_uom_qty = 2
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = gamejoy_xl_gray
            move_line.product_uom_qty = 10
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = gamejoy_xl_blue
            move_line.product_uom_qty = 12
        receipt_2 = receipt_form.save()
        receipt_2.action_confirm()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_template.ids)
        self.assertEqual(len(lines), 5, "Must have 5 lines.")
        self.assertEqual(docs['product_variants'].ids, product_template.product_variant_ids.ids)

        # Create a delivery for one of these products and check the report lines
        # are correctly linked to the good receipts.
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = gamejoy_pocket_gray
            move_line.product_uom_qty = 10
        delivery = delivery_form.save()
        delivery.action_confirm()

        report_values, docs, lines = self.get_report_forecast(product_template_ids=product_template.ids)
        self.assertEqual(len(lines), 5, "Still must have 5 lines.")
        self.assertEqual(docs['product_variants'].ids, product_template.product_variant_ids.ids)
        # First and second lines should be about the "Game Joy Pocket (gray)"
        # and must link the delivery with the two receipt lines.
        line_1 = lines[0]
        line_2 = lines[1]
        self.assertEqual(line_1['product']['id'], gamejoy_pocket_gray.id)
        self.assertEqual(line_1['quantity'], 8)
        self.assertTrue(line_1['replenishment_filled'])
        self.assertEqual(line_1['document_in'].id, receipt_1.id)
        self.assertEqual(line_1['document_out'].id, delivery.id)
        self.assertEqual(line_2['product']['id'], gamejoy_pocket_gray.id)
        self.assertEqual(line_2['quantity'], 2)
        self.assertTrue(line_2['replenishment_filled'])
        self.assertEqual(line_2['document_in'].id, receipt_2.id)
        self.assertEqual(line_2['document_out'].id, delivery.id)
