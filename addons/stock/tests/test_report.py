# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo.tests.common import Form, TransactionCase


class TestReportsCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Partner'})
        cls.ModelDataObj = cls.env['ir.model.data']
        cls.picking_type_in = cls.env['stock.picking.type'].browse(cls.ModelDataObj._xmlid_to_res_id('stock.picking_type_in'))
        cls.picking_type_out = cls.env['stock.picking.type'].browse(cls.ModelDataObj._xmlid_to_res_id('stock.picking_type_out'))
        cls.supplier_location = cls.env['stock.location'].browse(cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_suppliers'))
        cls.stock_location = cls.env['stock.location'].browse(cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_stock'))

        product_form = Form(cls.env['product.product'])
        product_form.detailed_type = 'product'
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
        lot1 = self.env['stock.lot'].create({
            'name': 'Volume-Beta',
            'product_id': product1.id,
            'company_id': self.env.company.id,
        })
        target = b'\n\n^XA\n^FO100,50\n^A0N,44,33^FD[C418]Mellohi^FS\n^FO100,100\n^A0N,44,33^FDLN/SN:Volume-Beta^FS\n^FO100,150^BY3\n^BCN,100,Y,N,N\n^FDVolume-Beta^FS\n^XZ\n'

        rendering, qweb_type = self.env['ir.actions.report']._render_qweb_text('stock.label_lot_template', lot1.id)
        self.assertEqual(target, rendering.replace(b' ', b''), 'The rendering is not good')
        self.assertEqual(qweb_type, 'text', 'the report type is not good')

    def test_report_quantity_1(self):
        product_form = Form(self.env['product.product'])
        product_form.detailed_type = 'product'
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
        }).action_apply_inventory()
        self.env.flush_all()
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
        self.env.flush_all()
        report_records_tomorrow = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today() + timedelta(days=1))],
            ['product_qty'], [])
        self.assertEqual(sum([r['product_qty'] for r in report_records_tomorrow]), 50.0)
        move_out._action_confirm()
        self.env.flush_all()
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
        self.env.flush_all()
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
        self.env.flush_all()
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
        product_form.detailed_type = 'product'
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
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product.id,
            'location_id': stock_without_wh.id,
            'inventory_quantity': 50
        }).action_apply_inventory()
        move = self.env['stock.move'].create({
            'name': 'Move outside warehouse',
            'location_id': stock.id,
            'location_dest_id': stock_without_wh.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10.0,
        })
        move._action_confirm()
        self.env.flush_all()
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
        self.env.flush_all()
        report_records = self.env['report.stock.quantity'].read_group(
            [('product_id', '=', product.id), ('date', '=', date.today())],
            ['product_qty', 'state'], ['state'], lazy=False)
        self.assertEqual(sum([r['product_qty'] for r in report_records if r['state'] == 'forecast']), 40.0)

    def test_report_quantity_3(self):
        product_form = Form(self.env['product.product'])
        product_form.detailed_type = 'product'
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

        self.env.flush_all()
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
        self.env.flush_all()
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
        self.env.flush_all()
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

    def test_report_forecast_8_delivery_to_receipt_link(self):
        """
        Create 2 deliveries, and 1 receipt tied to the second delivery.
        The report should show the source document as the 2nd delivery, and show the first
        delivery completely unfilled.
        """
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 100
        delivery = delivery_form.save()
        delivery.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 200
        delivery2 = delivery_form.save()
        delivery2.action_confirm()

        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt = receipt_form.save()
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 200
        receipt = receipt_form.save()
        receipt.move_ids[0].write({
            'move_dest_ids': [(4, delivery2.move_ids[0].id)],
        })
        receipt.action_confirm()

        # Test compute _compute_forecast_information
        self.assertEqual(delivery.move_ids.forecast_availability, -100)
        self.assertEqual(delivery2.move_ids.forecast_availability, 200)
        self.assertFalse(delivery.move_ids.forecast_expected_date)
        self.assertEqual(delivery2.move_ids.forecast_expected_date, receipt.move_ids.date)

        _, _, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)

        self.assertEqual(len(lines), 2, 'Only 2 lines')
        delivery_line = [l for l in lines if l['document_out'].id == delivery.id][0]
        self.assertTrue(delivery_line, 'No line for delivery 1')
        self.assertFalse(delivery_line['replenishment_filled'])
        delivery2_line = [l for l in lines if l['document_out'].id == delivery2.id][0]
        self.assertTrue(delivery2_line, 'No line for delivery 2')
        self.assertTrue(delivery2_line['replenishment_filled'])

    def test_report_forecast_9_delivery_to_receipt_link_over_received(self):
        """
        Create 2 deliveries, and 1 receipt tied to the second delivery.
        Set the quantity on the receipt to be enough for BOTH deliveries.
        For example, this can happen if they have manually increased the quantity on the generated PO.
        The report should show both deliveries fulfilled.
        """
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 100
        delivery = delivery_form.save()
        delivery.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 200
        delivery2 = delivery_form.save()
        delivery2.action_confirm()

        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt = receipt_form.save()
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 300
        receipt = receipt_form.save()
        receipt.move_ids[0].write({
            'move_dest_ids': [(4, delivery2.move_ids[0].id)],
        })
        receipt.action_confirm()

        # Test compute _compute_forecast_information
        self.assertEqual(delivery.move_ids.forecast_availability, 100)
        self.assertEqual(delivery2.move_ids.forecast_availability, 200)
        self.assertEqual(delivery.move_ids.forecast_expected_date, receipt.move_ids.date)
        self.assertEqual(delivery2.move_ids.forecast_expected_date, receipt.move_ids.date)

        _, _, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)

        self.assertEqual(len(lines), 2, 'Only 2 lines')
        delivery_line = [l for l in lines if l['document_out'].id == delivery.id][0]
        self.assertTrue(delivery_line, 'No line for delivery 1')
        self.assertTrue(delivery_line['replenishment_filled'])
        delivery2_line = [l for l in lines if l['document_out'].id == delivery2.id][0]
        self.assertTrue(delivery2_line, 'No line for delivery 2')
        self.assertTrue(delivery2_line['replenishment_filled'])

    def test_report_forecast_10_report_line_corresponding_to_picking_highlighted(self):
        """ When accessing the report from a stock move, checks if the correct picking is highlighted in the report
            and if the forecasted availability for incoming and outcoming moves is correct
        """
        # Creation of one delivery with date 'today'
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        delivery_form.scheduled_date = date.today()
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 200
        delivery1 = delivery_form.save()
        delivery1.action_confirm()

        # Creation of one receipt with date 'today + 1' and smaller qty than the delivery
        scheduled_date1 = datetime.now() + timedelta(days=1)
        receipt_form = Form(self.env['stock.picking'])
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.scheduled_date = scheduled_date1
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 150
        receipt1 = receipt_form.save()
        receipt1.action_confirm()
        self.assertEqual(receipt1.move_ids.forecast_availability, -50.0)
        self.assertEqual(delivery1.move_ids.forecast_availability, 150)
        self.assertEqual(delivery1.move_ids.forecast_expected_date, scheduled_date1)

        # Creation of an identical receipt which should lead to a positive forecast availability
        scheduled_date2 = datetime.now() + timedelta(days=3)
        receipt_form = Form(self.env['stock.picking'])
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.scheduled_date = scheduled_date2
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 150
        receipt2 = receipt_form.save()
        receipt2.action_confirm()
        for move in receipt2.move_ids:
            move.quantity_done = 150

        # Check forecast_information of delivery1
        delivery1.move_ids._compute_forecast_information()  # Because depends not "complete"
        self.assertEqual(delivery1.move_ids.forecast_availability, 200)
        self.assertEqual(delivery1.move_ids.forecast_expected_date, scheduled_date2)

        receipt2.button_validate()
        self.assertEqual(receipt1.move_ids.forecast_availability, 100.0)

        # Check forecast_information of delivery1, because the receipt2 as been validate the forecast_expected_date == receipt1.scheduled_date
        delivery1.move_ids._compute_forecast_information()
        self.assertEqual(delivery1.move_ids.forecast_availability, 200)
        self.assertEqual(delivery1.move_ids.forecast_expected_date, scheduled_date1)

        delivery2 = delivery1.copy()
        delivery2_form = Form(delivery2)
        delivery2_form.scheduled_date = datetime.now() + timedelta(days=1)
        delivery2 = delivery2_form.save()
        delivery2.action_confirm()
        self.assertEqual(delivery2.move_ids.forecast_availability, 100)

        # Check for both deliveries and receipts if the highlight (is_matched) corresponds to the correct picking
        for picking in [delivery1, delivery2, receipt1, receipt2]:
            context = picking.move_ids[0].action_product_forecast_report()['context']
            _, _, lines = self.get_report_forecast(product_template_ids=self.product_template.ids, context=context)
            for line in lines:
                if picking in [line['document_in'], line['document_out']]:
                    self.assertTrue(line['is_matched'], "The corresponding picking should be matched in the forecast report.")
                else:
                    self.assertFalse(line['is_matched'], "A line of the forecast report not linked to the picking shoud not be matched.")

    def test_report_forecast_11_non_reserved_order(self):
        """ Creates deliveries with different operation type reservation methods.
        Checks replenishment lines are correctly sorted by reservation_date:
            'manual': always last (no reservation_date)
            'at_confirm': reservation_date = time of creation
            'by_date': reservation_date = scheduled_date - reservation_days_before(_priority)
        """

        picking_type_manual = self.picking_type_out.copy()
        picking_type_by_date = picking_type_manual.copy()
        picking_type_at_confirm = picking_type_manual.copy()
        picking_type_manual.reservation_method = 'manual'
        picking_type_manual.sequence_code = 'manual'
        picking_type_by_date.reservation_method = 'by_date'
        picking_type_by_date.sequence_code = 'by'
        # artificially make non-priority moves reserve before priority moves to
        # check order doesn't prioritize priority
        picking_type_by_date.reservation_days_before = '6'
        picking_type_by_date.reservation_days_before_priority = '4'
        picking_type_at_confirm.reservation_method = 'at_confirm'
        picking_type_at_confirm.sequence_code = 'confirm'

        # 'manual' reservation => no reservation_date
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_manual
        delivery_form.scheduled_date = datetime.now() - timedelta(days=10)
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery_manual = delivery_form.save()
        delivery_manual.action_confirm()

        # 'by_date' reservation => reservation_date = 1 day before today
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_by_date
        delivery_form.scheduled_date = datetime.now() + timedelta(days=5)
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery_by_date = delivery_form.save()
        delivery_by_date.action_confirm()

        # 'by_date' reservation (priority) => reservation_date = 1 day after today
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_by_date
        delivery_form.scheduled_date = datetime.now() + timedelta(days=5)
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery_by_date_priority = delivery_form.save()
        # <field name="priority" attrs="{'invisible': [('name','=','/')]}"/>
        # The priority field is not visible until the name is set,
        # which is done after a first save / the `create`
        delivery_form.priority = '1'
        delivery_by_date_priority = delivery_form.save()
        delivery_by_date_priority.action_confirm()

        # 'at_confirm' reservation => reservation_date = today
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_at_confirm
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        delivery_at_confirm = delivery_form.save()
        delivery_at_confirm.action_confirm()

        # Order should be: delivery_by_date, delivery_at_confirm, delivery_by_date_priority, delivery_manual
        _, _, lines = self.get_report_forecast(product_template_ids=self.product_template.ids)
        self.assertEqual(len(lines), 4, "The report must have 4 lines.")
        self.assertEqual(lines[0]['document_out'].id, delivery_by_date.id)
        self.assertEqual(lines[1]['document_out'].id, delivery_at_confirm.id)
        self.assertEqual(lines[2]['document_out'].id, delivery_by_date_priority.id)
        self.assertEqual(lines[3]['document_out'].id, delivery_manual.id)

        all_delivery = delivery_by_date | delivery_at_confirm | delivery_by_date_priority | delivery_manual
        self.assertEqual(all_delivery.move_ids.mapped("forecast_availability"), [-3.0, -3.0, -3.0, -3.0])

        # Creation of one receipt to fulfill the 2 first deliveries delivery_by_date and delivery_at_confirm
        receipt_form = Form(self.env['stock.picking'])
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        receipt_form.scheduled_date = date.today() + timedelta(days=1)
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 6
        receipt1 = receipt_form.save()
        receipt1.action_confirm()

        self.assertEqual(all_delivery.move_ids.mapped("forecast_availability"), [3, 3, -3.0, -3.0])

    def test_report_reception_1_one_receipt(self):
        """ Create 2 deliveries and 1 receipt where some of the products being received
        can be reserved for the deliveries. Check that the reception report correctly
        shows these corresponding potential allocations + correctly reserves incoming moves
        when reserve button is pushed.
        """
        product2 = self.env['product.product'].create({
            'name': 'Extra Product',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        product3 = self.env['product.product'].create({
            'name': 'Unpopular Product',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        # Creates some deliveries for reception report to match against
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = product2
            move_line.product_uom_qty = 10
        delivery1 = delivery_form.save()
        delivery1.action_confirm()

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 2
        delivery2 = delivery_form.save()
        delivery2.action_confirm()

        # Create a receipt
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            # incoming qty greater than total (2 moves) outgoing amount => 2 report lines, each = outgoing qty
            move_line.product_id = self.product
            move_line.product_uom_qty = 15
        with receipt_form.move_ids_without_package.new() as move_line:
            # outgoing qty greater than incoming amount => report line = incoming qty
            move_line.product_id = product2
            move_line.product_uom_qty = 5
        with receipt_form.move_ids_without_package.new() as move_line:
            # not outgoing => shouldn't appear in report
            move_line.product_id = product3
            move_line.product_uom_qty = 5
        receipt = receipt_form.save()

        # check that reception report has correct number of deliveries/outgoing moves
        # but the quantities aren't available for assignment yet (i.e. can link as chained moves)
        report = self.env['report.stock.report_reception']
        report_values = report._get_report_values(docids=[receipt.id])
        sources_to_lines = report_values['sources_to_lines']
        self.assertEqual(len(sources_to_lines), 2, "The report has wrong number of outgoing pickings.")
        all_lines = []
        for dummy, lines in sources_to_lines.items():
            for line in lines:
                self.assertFalse(line['is_qty_assignable'], "The receipt IS DRAFT => its move quantities ARE NOT available to assign.")
                all_lines.append(line)
        self.assertEqual(len(all_lines), 3, "The report has wrong number of outgoing moves.")
        # we expect this order based on move creation
        self.assertEqual(all_lines[0]['quantity'], 5, "The first move has wrong incoming qty.")
        self.assertEqual(all_lines[0]['product']['id'], self.product.id, "The first move has wrong incoming product to assign.")
        self.assertEqual(all_lines[1]['quantity'], 5, "The second move has wrong incoming qty.")
        self.assertEqual(all_lines[1]['product']['id'], product2.id, "The second move has wrong incoming product to assign.")
        self.assertEqual(all_lines[2]['quantity'], 2, "The last move has wrong incoming qty.")
        self.assertEqual(all_lines[2]['product']['id'], self.product.id, "The third move has wrong incoming product to assign.")

        # check that report correctly realizes outgoing moves can be linked when receipt is done
        receipt.action_confirm()
        for move in receipt.move_ids:
            move.quantity_done = move.product_uom_qty
        receipt.button_validate()
        report_values = report._get_report_values(docids=[receipt.id])

        sources_to_lines = report_values['sources_to_lines']
        all_lines = []
        move_ids = []
        qtys = []
        in_ids = []
        for dummy, lines in sources_to_lines.items():
            for line in lines:
                self.assertTrue(line['is_qty_assignable'], "The receipt IS DONE => all of its move quantities ARE assignable")
                all_lines.append(line)
                move_ids.append(line['move_out'].id)
                qtys.append(line['quantity'])
                in_ids += line['move_ins']
        # line quantities should be the same when receipt is done compared to when it was draft
        self.assertEqual(len(all_lines), 3, "The report has wrong number of outgoing moves.")
        self.assertEqual(all_lines[0]['quantity'], 5, "The first move has wrong incoming qty to reserve.")
        self.assertEqual(all_lines[0]['product']['id'], self.product.id, "The first move has wrong product to reserve.")
        self.assertEqual(all_lines[1]['quantity'], 5, "The second move has wrong incoming qty to reserve.")
        self.assertEqual(all_lines[1]['product']['id'], product2.id, "The second move has wrong product to reserve.")
        self.assertEqual(all_lines[2]['quantity'], 2, "The last move has wrong incoming qty to reserve.")
        self.assertEqual(all_lines[2]['product']['id'], self.product.id, "The third move has wrong product to reserve.")

        # check that report assign button works correctly
        report.action_assign(move_ids, qtys, in_ids)
        self.assertEqual(len(receipt.move_ids[0].move_dest_ids.ids), 2, "Demand qty of first and last moves should now be linked to incoming.")
        self.assertEqual(len(receipt.move_ids[1].move_dest_ids.ids), 1, "Demand qty of second move should now be linked to incoming.")
        self.assertEqual(len(receipt.move_ids[2].move_dest_ids.ids), 0, "product3 should have no moves linked to it.")
        self.assertEqual(len(delivery1.move_ids.filtered(lambda m: m.product_id == product2)), 2, "product2 outgoing move should be split between linked and non-linked quantities.")

    def test_report_reception_2_two_receipts(self):
        """ Create 1 delivery and 2 receipts where the products being received
        can be reserved for the delivery. Check that the reception report correctly
        shows corresponding potential allocations when receipts have differing states.
        """
        # Creates delivery for reception report to match against
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 100
        delivery = delivery_form.save()
        delivery.action_confirm()

        # Create 2 receipts and check its reception report values
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 5
        receipt1 = receipt_form.save()

        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 3
        receipt2 = receipt_form.save()

        # check that report correctly merges not draft incoming quantities
        report = self.env['report.stock.report_reception']
        report_values = report._get_report_values(docids=[receipt1.id, receipt2.id])
        self.assertEqual(len(report_values['docs']), 2, "There should be 2 receipts to assign from in this report")
        sources_to_lines = report_values['sources_to_lines']
        self.assertEqual(len(sources_to_lines), 1, "The report has wrong number of outgoing pickings.")
        all_lines = list(sources_to_lines.values())[0]
        self.assertEqual(len(all_lines), 1, "The report has wrong number of outgoing move lines.")
        self.assertFalse(all_lines[0]['is_qty_assignable'], "The receipt IS NOT done => its move quantities ARE NOT available to reserve (i.e. done).")
        self.assertEqual(all_lines[0]['quantity'], 8, "The move has wrong incoming qty.")

        # check that report splits assignable and non-assignable quantities when 1 receipt is draft and other is confirmed
        receipt1.action_confirm()
        for move in receipt1.move_ids:
            move.quantity_done = move.product_uom_qty
        report_values = report._get_report_values(docids=[receipt1.id, receipt2.id])

        sources_to_lines = report_values['sources_to_lines']
        all_lines = list(sources_to_lines.values())[0]
        # line quantities depends on done vs not done incoming quantities => should be 2 lines now
        self.assertEqual(len(all_lines), 2, "The report has wrong number of lines (1 assignable + 1 not).")
        self.assertEqual(all_lines[0]['quantity'], 5, "The first move has wrong incoming qty to assign.")
        self.assertTrue(all_lines[0]['is_qty_assignable'], "1 receipt is done => should have 1 reservable move.")
        self.assertEqual(all_lines[1]['quantity'], 3, "The second move has wrong (expected) incoming qty.")
        self.assertFalse(all_lines[1]['is_qty_assignable'], "1 receipt is draft => should have 1 non-assignable move.")

        # check that report doesn't allow done and non-done moves at same time
        receipt1.button_validate()
        reason = report._get_report_values(docids=[receipt1.id, receipt2.id])['reason']
        self.assertEqual(reason, "This report cannot be used for done and not done %s at the same time" % report._get_doc_types(), "empty report reason not shown")

    def test_report_reception_3_multiwarehouse(self):
        """ Check that reception report respects same warehouse for
        receipts and deliveries.
        """
        # Warehouse config.
        wh_2 = self.env['stock.warehouse'].create({
            'name': 'Other Warehouse',
            'code': 'OTHER',
        })
        picking_type_out_2 = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('warehouse_id', '=', wh_2.id),
        ])

        # Creates delivery in warehouse2
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = picking_type_out_2
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 100
        delivery = delivery_form.save()
        delivery.action_confirm()

        # Create a receipt in warehouse1
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 15
        receipt = receipt_form.save()

        report = self.env['report.stock.report_reception']
        report_values = report._get_report_values(docids=[receipt.id])
        self.assertEqual(len(report_values['sources_to_lines']), 0, "The receipt and delivery are in different warehouses => no moves to link to should be found.")

    def test_report_reception_4_pick_pack(self):
        """ Check that reception report ignores outgoing moves that are not beginning of chain
        """

        warehouse = self.env['stock.warehouse'].search([('lot_stock_id', '=', self.stock_location.id)], limit=1)
        warehouse.write({'delivery_steps': 'pick_pack_ship'})

        ship_move = self.env['stock.move'].create({
            'name': 'The ship move',
            'product_id': self.product.id,
            'product_uom_qty': 5.0,
            'product_uom': self.product.uom_id.id,
            'location_id': warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'warehouse_id': warehouse.id,
            'picking_type_id': warehouse.out_type_id.id,
            'procure_method': 'make_to_order',
            'state': 'draft',
        })

        # create chained pick/pack moves to test with
        ship_move._assign_picking()
        ship_move._action_confirm()
        pack_move = ship_move.move_orig_ids[0]
        pick_move = pack_move.move_orig_ids[0]

        self.assertEqual(pack_move.state, 'waiting', "Pack move wasn't created...")
        self.assertEqual(pick_move.state, 'confirmed', "Pick move wasn't created...")

        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = 15
        receipt = receipt_form.save()

        report = self.env['report.stock.report_reception']
        report_values = report._get_report_values(docids=[receipt.id])
        self.assertEqual(len(report_values['sources_to_lines']), 1, "There should only be 1 line (pick move)")

    def test_report_reception_5_move_splitting(self):
        """ Check the complicated use cases of correct move splitting when assigning/unassigning when:
        1. Qty to assign is less than delivery qty demand
        2. Delivery already has some reserved quants
        """
        incoming_qty = 4
        outgoing_qty = 10
        qty_in_stock = outgoing_qty - incoming_qty
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': qty_in_stock
        }).action_apply_inventory()

        # create delivery + receipt
        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = outgoing_qty
        delivery = delivery_form.save()
        delivery.action_confirm()

        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = incoming_qty
        receipt = receipt_form.save()
        receipt.action_confirm()

        self.assertEqual(len(delivery.move_ids_without_package), 1)
        report = self.env['report.stock.report_reception']

        # -------------------
        # check report assign
        # -------------------
        report.action_assign(delivery.move_ids_without_package.ids, [incoming_qty], receipt.move_ids_without_package.ids)
        mto_move = delivery.move_ids_without_package.filtered(lambda m: m.procure_method == 'make_to_order')
        non_mto_move = delivery.move_ids_without_package - mto_move

        # check that delivery move splits correctly when receipt move is assigned to it
        self.assertEqual(len(delivery.move_ids_without_package), 2, "Delivery moves should have split into assigned + not assigned")
        self.assertEqual(len(delivery.move_ids_without_package.mapped('move_orig_ids')), 1, "Only 1 delivery + 1 receipt move should be assigned")
        self.assertEqual(len(receipt.move_ids_without_package.mapped('move_dest_ids')), 1, "Receipt move should remain unsplit")

        # check that assigned (MTO) move is correctly created
        self.assertEqual(len(mto_move), 1, "Only 1 delivery move should be MTO")
        self.assertEqual(mto_move.product_uom_qty, incoming_qty, "Incorrect quantity split for MTO move")
        self.assertEqual(mto_move.reserved_availability, 0, "Receipt is not done => assigned move can't have a reserved qty")
        self.assertEqual(mto_move.state, 'waiting', "MTO move state not correctly set")

        # check that non-assigned move has correct values
        self.assertEqual(non_mto_move.product_uom_qty, outgoing_qty - incoming_qty, "Incorrect quantity split for non-MTO move")
        self.assertEqual(non_mto_move.reserved_availability, qty_in_stock, "Reserved qty not correctly linked to non-MTO move")
        self.assertEqual(non_mto_move.state, 'assigned', "Fully reserved move has not correctly set state")

        # ---------------------
        # check report unassign
        # ---------------------
        report.action_unassign([mto_move.id], incoming_qty, receipt.move_ids_without_package.ids)
        self.assertEqual(mto_move.product_uom_qty, incoming_qty, "Move quantities should be unchanged")
        self.assertEqual(mto_move.procure_method, 'make_to_stock', "Procure method not correctly reset")
        self.assertEqual(mto_move.state, 'confirmed', "Move state not correctly reset (to non-MTO state)")

    def test_report_reception_6_backorders(self):
        """ Check the complicated use case with backorder when:
        1. Incoming qty is greater than outgoing qty needed to be assigned + total outgoing qty is assigned
        2. Smaller qty is completed + backorder is made for rest
        3. Backorder qty (which is still assigned) is unassigned + re-assigned
        """
        incoming_qty = 10
        outgoing_qty = 8
        orig_incoming_qty_done = 4

        delivery_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = outgoing_qty
        delivery = delivery_form.save()
        delivery.action_confirm()

        # Create receipt w/greater qty than needed delivery qty
        receipt_form = Form(self.env['stock.picking'].with_context(
            force_detailed_view=True
        ), view='stock.view_picking_form')
        receipt_form.partner_id = self.partner
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move_line:
            move_line.product_id = self.product
            move_line.product_uom_qty = incoming_qty
        receipt = receipt_form.save()
        receipt.action_confirm()

        report = self.env['report.stock.report_reception']
        report.action_assign(delivery.move_ids_without_package.ids, [outgoing_qty], receipt.move_ids_without_package.ids)
        self.assertEqual(receipt.move_ids_without_package.move_dest_ids.ids, delivery.move_ids_without_package.ids, "Link between receipt and delivery moves should have been made")

        for move in receipt.move_ids:
            move.quantity_done = orig_incoming_qty_done
        res_dict = receipt.button_validate()
        backorder_wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        backorder_wizard.process()
        backorder = self.env['stock.picking'].search([('backorder_id', '=', receipt.id)])

        # Check backorder assigned quantities
        self.assertEqual(receipt.move_ids_without_package.move_dest_ids, backorder.move_ids_without_package.move_dest_ids, "Backorder should have copied link to delivery move")
        report_values = report._get_report_values(docids=[backorder.id])
        sources_to_lines = report_values['sources_to_lines']
        all_lines = list(sources_to_lines.values())[0]
        self.assertEqual(len(all_lines), 1, "The report has wrong number of outgoing moves.")
        # we expect that the report won't know about original receipt done amount, so it will show outgoing_qty as assigned
        # (rather than the remaining amount that isn't reserved). This can change if the report becomes more sophisticated
        self.assertEqual(all_lines[0]['quantity'], incoming_qty - orig_incoming_qty_done, "The report doesn't have the correct qty assigned.")

        # Unassign the amount we expect to see in the report + check split correctly happens
        report.action_unassign(delivery.move_ids_without_package.ids, outgoing_qty, backorder.move_ids_without_package.ids)
        self.assertEqual(len(delivery.move_ids_without_package), 2, "The delivery should have split its reserved qty from the original move")
        reserved_move = receipt.move_ids_without_package.move_dest_ids
        self.assertEqual(len(reserved_move), 1, "Move w/reserved qty should have full demand reserved")
        self.assertEqual(reserved_move.state, 'assigned', "Move w/reserved qty should have full demand reserved")
        self.assertEqual(reserved_move.product_uom_qty, orig_incoming_qty_done, "Done amount in original receipt should be amount demanded/reserved in delivery still with a link")
        report_values = report._get_report_values(docids=[backorder.id])
        sources_to_lines = report_values['sources_to_lines']
        all_lines = list(sources_to_lines.values())[0]
        self.assertEqual(len(all_lines), 1, "The report should only contain the remaining non-reserved move")
        self.assertEqual(all_lines[0]['quantity'], outgoing_qty - orig_incoming_qty_done, "The report doesn't have the correct qty to assign")

        # Re-assign the remaining delivery amount and check that everything reserves correctly in the end
        report.action_assign((delivery.move_ids_without_package - reserved_move).ids, [outgoing_qty - orig_incoming_qty_done], backorder.move_ids_without_package.ids)
        for move in backorder.move_ids:
            move.quantity_done = incoming_qty - orig_incoming_qty_done
        backorder.button_validate()
        for move in delivery.move_ids_without_package:
            self.assertEqual(move.state, 'assigned', "All delivery moves should be fully reserved now")
