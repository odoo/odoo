# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.tests.common import Form


class TestStockProductionLot(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super(TestStockProductionLot, cls).setUpClass()
        # Creates a tracked product with expiration dates.
        cls.apple_product = cls.ProductObj.create({
            'name': 'Apple',
            'type': 'product',
            'tracking': 'lot',
            'use_expiration_date': True,
            'expiration_time': 10,
            'use_time': 5,
            'removal_time': 8,
            'alert_time': 4,
        })

    def test_00_stock_production_lot(self):
        """ Test Scheduled Task on lot with an alert_date in the past creates an activity """

        # create product 
        self.productAAA = self.ProductObj.create({
            'name': 'Product AAA',
            'type': 'product',
            'tracking':'lot',
            'company_id': self.env.company.id,
        })

        # create a new lot with with alert date in the past
        self.lot1_productAAA = self.LotObj.create({
            'name': 'Lot 1 ProductAAA',
            'product_id': self.productAAA.id,
            'alert_date': fields.Date.to_string(datetime.today() - relativedelta(days=15)),
            'company_id': self.env.company.id,
        })

        picking_in = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location
        })

        move_a = self.MoveObj.create({
            'name': self.productAAA.name,
            'product_id': self.productAAA.id,
            'product_uom_qty': 33,
            'product_uom': self.productAAA.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location
        })
        
        self.assertEqual(picking_in.move_lines.state, 'draft', 'Wrong state of move line.')
        picking_in.action_confirm()
        self.assertEqual(picking_in.move_lines.state, 'assigned', 'Wrong state of move line.')

        # Replace pack operation of incoming shipments.
        picking_in.action_assign()
        move_a.move_line_ids.qty_done = 33
        move_a.move_line_ids.lot_id = self.lot1_productAAA.id

        # Transfer Incoming Shipment.
        picking_in._action_done()

        # run scheduled tasks
        self.env['stock.production.lot']._alert_date_exceeded()

        # check a new activity has been created
        activity_id = self.env.ref('product_expiry.mail_activity_type_alert_date_reached').id
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productAAA.id)
        ])
        self.assertEqual(activity_count, 1, 'No activity created while there should be one')

        # run the scheduler a second time
        self.env['stock.production.lot']._alert_date_exceeded()

        # check there is still only one activity, no additional activity is created if there is already an existing activity
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productAAA.id)
        ])
        self.assertEqual(activity_count, 1, 'There should be one and only one activity')

        # mark the activity as done
        mail_activity = self.env['mail.activity'].search([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productAAA.id)
        ])
        mail_activity.action_done()

        # check there is no more activity (because it is already done)
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productAAA.id)
        ])
        self.assertEqual(activity_count, 0,"As activity is done, there shouldn't be any related activity")
                
        # run the scheduler a third time
        self.env['stock.production.lot']._alert_date_exceeded()

        # check there is no activity created
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=',self.lot1_productAAA.id)
        ])
        self.assertEqual(activity_count, 0, "As there is already an activity marked as done, there shouldn't be any related activity created for this lot")

    def test_01_stock_production_lot(self):
        """ Test Scheduled Task on lot with an alert_date in future does not create an activity """

        # create product 
        self.productBBB = self.ProductObj.create({
            'name': 'Product BBB', 
            'type': 'product',
            'tracking':'lot'
        })

        # create a new lot with with alert date in the past
        self.lot1_productBBB = self.LotObj.create({
            'name': 'Lot 1 ProductBBB',
            'product_id': self.productBBB.id,
            'alert_date': fields.Date.to_string(datetime.today() + relativedelta(days=15)),
            'company_id': self.env.company.id,
        })

        picking_in = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        move_b = self.MoveObj.create({
            'name': self.productBBB.name,
            'product_id': self.productBBB.id,
            'product_uom_qty': 44,
            'product_uom': self.productBBB.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        
        self.assertEqual(picking_in.move_lines.state, 'draft', 'Wrong state of move line.')
        picking_in.action_confirm()
        self.assertEqual(picking_in.move_lines.state, 'assigned', 'Wrong state of move line.')

        # Replace pack operation of incoming shipments.
        picking_in.action_assign()
        move_b.move_line_ids.qty_done = 44
        move_b.move_line_ids.lot_id = self.lot1_productBBB.id

        # Transfer Incoming Shipment.
        picking_in._action_done()

        # run scheduled tasks
        self.env['stock.production.lot']._alert_date_exceeded()

        # check a new activity has not been created
        activity_id = self.env.ref('product_expiry.mail_activity_type_alert_date_reached').id
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productBBB.id)
        ])
        self.assertEqual(activity_count, 0, "An activity has been created while it shouldn't")

    def test_02_stock_production_lot(self):
        """ Test Scheduled Task on lot without an alert_date does not create an activity """

        # create product 
        self.productCCC = self.ProductObj.create({'name': 'Product CCC', 'type': 'product', 'tracking':'lot'})

        # create a new lot with with alert date in the past
        self.lot1_productCCC = self.LotObj.create({'name': 'Lot 1 ProductCCC', 'product_id': self.productCCC.id, 'company_id': self.env.company.id})

        picking_in = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})

        move_c = self.MoveObj.create({
            'name': self.productCCC.name,
            'product_id': self.productCCC.id,
            'product_uom_qty': 44,
            'product_uom': self.productCCC.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location})
        
        self.assertEqual(picking_in.move_lines.state, 'draft', 'Wrong state of move line.')
        picking_in.action_confirm()
        self.assertEqual(picking_in.move_lines.state, 'assigned', 'Wrong state of move line.')

        # Replace pack operation of incoming shipments.
        picking_in.action_assign()
        move_c.move_line_ids.qty_done = 55
        move_c.move_line_ids.lot_id = self.lot1_productCCC.id

        # Transfer Incoming Shipment.
        picking_in._action_done()

        # run scheduled tasks
        self.env['stock.production.lot']._alert_date_exceeded()

        # check a new activity has not been created
        activity_id = self.env.ref('product_expiry.mail_activity_type_alert_date_reached').id
        activity_count = self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', self.env.ref('stock.model_stock_production_lot').id),
            ('res_id', '=', self.lot1_productCCC.id)
        ])
        self.assertEqual(activity_count, 0, "An activity has been created while it shouldn't")

    def test_03_onchange_expiration_date(self):
        """ Updates the `expiration_date` of the lot production and checks other date
        fields are updated as well. """
        # Keeps track of the current datetime and set a delta for the compares.
        today_date = datetime.today()
        time_gap = timedelta(seconds=10)
        # Creates a new lot number and saves it...
        lot_form = Form(self.LotObj)
        lot_form.name = 'Apple Box #1'
        lot_form.product_id = self.apple_product
        lot_form.company_id = self.env.company
        apple_lot = lot_form.save()
        # ...then checks date fields have the expected values.
        exp_date = apple_lot.expiration_date
        self.assertAlmostEqual(
            today_date + timedelta(days=self.apple_product.expiration_time),
            exp_date, delta=time_gap)
        self.assertAlmostEqual(
            exp_date - timedelta(days=self.apple_product.use_time),
            apple_lot.use_date, delta=time_gap)
        self.assertAlmostEqual(
            exp_date - timedelta(days=self.apple_product.removal_time),
            apple_lot.removal_date, delta=time_gap)
        self.assertAlmostEqual(
            exp_date - timedelta(days=self.apple_product.alert_time),
            apple_lot.alert_date, delta=time_gap)

        difference = timedelta(days=20)
        new_date = apple_lot.expiration_date + difference
        old_use_date = apple_lot.use_date
        old_removal_date = apple_lot.removal_date
        old_alert_date = apple_lot.alert_date

        # Modifies the lot `expiration_date`...
        lot_form = Form(apple_lot)
        lot_form.expiration_date = new_date
        apple_lot = lot_form.save()

        # ...then checks all other date fields were correclty updated.
        self.assertAlmostEqual(
            apple_lot.use_date, old_use_date + difference, delta=time_gap)
        self.assertAlmostEqual(
            apple_lot.removal_date, old_removal_date + difference, delta=time_gap)
        self.assertAlmostEqual(
            apple_lot.alert_date, old_alert_date + difference, delta=time_gap)

    def test_04_expiration_date_on_receipt(self):
        """ Test we can set an expiration date on receipt and all expiration
        date will be correctly set. """
        partner = self.env['res.partner'].create({
            'name': 'Apple\'s Joe',
            'company_id': self.env.ref('base.main_company').id,
        })
        expiration_date = datetime.today() + timedelta(days=30)
        time_gap = timedelta(seconds=10)

        # Receives a tracked production using expiration date.
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 4
        receipt = picking_form.save()
        receipt.action_confirm()

        # Defines a date during the receipt.
        move_form = Form(receipt.move_ids_without_package, view="stock.view_stock_move_operations")
        with move_form.move_line_ids.new() as line:
            line.lot_name = 'Apple Box #2'
            line.expiration_date = expiration_date
            line.qty_done = 4
        move = move_form.save()

        receipt._action_done()
        # Get back the lot created when the picking was done...
        apple_lot = self.env['stock.production.lot'].search(
            [('product_id', '=', self.apple_product.id)],
            limit=1,
        )
        # ... and checks all date fields are correctly set.
        self.assertAlmostEqual(
            apple_lot.expiration_date, expiration_date, delta=time_gap)
        self.assertAlmostEqual(
            apple_lot.use_date, expiration_date - timedelta(days=self.apple_product.use_time), delta=time_gap)
        self.assertAlmostEqual(
            apple_lot.removal_date, expiration_date - timedelta(days=self.apple_product.removal_time), delta=time_gap)
        self.assertAlmostEqual(
            apple_lot.alert_date, expiration_date - timedelta(days=self.apple_product.alert_time), delta=time_gap)

    def test_04_2_expiration_date_on_receipt(self):
        """ Test we can set an expiration date on receipt even if all expiration
        date related fields aren't set on product. """
        partner = self.env['res.partner'].create({
            'name': 'Apple\'s Joe',
            'company_id': self.env.ref('base.main_company').id,
        })
        # Unset some fields.
        self.apple_product.expiration_time = False
        self.apple_product.removal_time = False

        expiration_date = datetime.today() + timedelta(days=30)
        time_gap = timedelta(seconds=10)

        # Receives a tracked production using expiration date.
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 4
        receipt = picking_form.save()
        receipt.action_confirm()

        # Defines a date during the receipt.
        move = receipt.move_ids_without_package[0]
        line = move.move_line_ids[0]
        self.assertEqual(move.use_expiration_date, True)
        line.lot_name = 'Apple Box #3'
        line.expiration_date = expiration_date
        line.qty_done = 4

        receipt._action_done()
        # Get back the lot created when the picking was done...
        apple_lot = self.env['stock.production.lot'].search(
            [('product_id', '=', self.apple_product.id)],
            limit=1,
        )
        # ... and checks all date fields are correctly set.
        self.assertAlmostEqual(
            apple_lot.expiration_date, expiration_date, delta=time_gap,
            msg="Must be define even if the product's `expiration_time` isn't set.")
        self.assertAlmostEqual(
            apple_lot.use_date, expiration_date - timedelta(days=self.apple_product.use_time), delta=time_gap)
        self.assertAlmostEqual(
            apple_lot.removal_date, expiration_date - timedelta(days=self.apple_product.removal_time), delta=time_gap,
            msg="`removal_date` should always be calculated when an expiration date is defined")
        self.assertAlmostEqual(
            apple_lot.alert_date, expiration_date - timedelta(days=self.apple_product.alert_time), delta=time_gap)

    def test_05_confirmation_on_delivery(self):
        """ Test when user tries to delivery expired lot, he/she gets a
        confirmation wizard. """
        partner = self.env['res.partner'].create({
            'name': 'Cider & Son',
            'company_id': self.env.ref('base.main_company').id,
        })
        # Creates 3 lots (1 non-expired lot, 2 expired lots)
        lot_form = Form(self.LotObj)  # Creates the lot.
        lot_form.name = 'good-apple-lot'
        lot_form.product_id = self.apple_product
        lot_form.company_id = self.env.company
        good_lot = lot_form.save()

        lot_form = Form(self.LotObj)  # Creates the lot.
        lot_form.name = 'expired-apple-lot-01'
        lot_form.product_id = self.apple_product
        lot_form.company_id = self.env.company
        expired_lot_1 = lot_form.save()
        lot_form = Form(expired_lot_1)  # Edits the lot to make it expired.
        lot_form.expiration_date = datetime.today() - timedelta(days=10)
        expired_lot_1 = lot_form.save()

        # Case #1: make a delivery with no expired lot.
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 4
        # Saves and confirms it...
        delivery_1 = picking_form.save()
        delivery_1.action_confirm()
        # ... then create a move line with the non-expired lot and valids the picking.
        delivery_1.move_line_ids_without_package = [(5, 0), (0, 0, {
            'company_id': self.env.company.id,
            'location_id': delivery_1.move_lines.location_id.id,
            'location_dest_id': delivery_1.move_lines.location_dest_id.id,
            'lot_id': good_lot.id,
            'product_id': self.apple_product.id,
            'product_uom_id': self.apple_product.uom_id.id,
            'qty_done': 4,
        })]
        res = delivery_1.button_validate()
        # Validate a delivery for good products must not raise anything.
        self.assertEqual(res, True)

        # Case #2: make a delivery with one non-expired lot and one expired lot.
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 8
        # Saves and confirms it...
        delivery_2 = picking_form.save()
        delivery_2.action_confirm()
        # ... then create a move line for the non-expired lot and for an expired
        # lot and valids the picking.
        delivery_2.move_line_ids_without_package = [(5, 0), (0, 0, {
            'company_id': self.env.company.id,
            'location_id': delivery_2.move_lines.location_id.id,
            'location_dest_id': delivery_2.move_lines.location_dest_id.id,
            'lot_id': good_lot.id,
            'product_id': self.apple_product.id,
            'product_uom_id': self.apple_product.uom_id.id,
            'qty_done': 4,
        }), (0, 0, {
            'company_id': self.env.company.id,
            'location_id': delivery_2.move_lines.location_id.id,
            'location_dest_id': delivery_2.move_lines.location_dest_id.id,
            'lot_id': expired_lot_1.id,
            'product_id': self.apple_product.id,
            'product_uom_id': self.apple_product.uom_id.id,
            'qty_done': 4,
        })]
        res = delivery_2.button_validate()
        # Validate a delivery containing expired products must raise a confirmation wizard.
        self.assertNotEqual(res, True)
        self.assertEqual(res['res_model'], 'expiry.picking.confirmation')

        # Case #3: make a delivery with only on expired lot.
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.apple_product
            move.product_uom_qty = 4
        # Saves and confirms it...
        delivery_3 = picking_form.save()
        delivery_3.action_confirm()
        # ... then create two move lines with expired lot and valids the picking.
        delivery_3.move_line_ids_without_package = [(5, 0), (0, 0, {
            'company_id': self.env.company.id,
            'location_id': delivery_3.move_lines.location_id.id,
            'location_dest_id': delivery_3.move_lines.location_dest_id.id,
            'lot_id': expired_lot_1.id,
            'product_id': self.apple_product.id,
            'product_uom_id': self.apple_product.uom_id.id,
            'qty_done': 4,
        })]
        res = delivery_3.button_validate()
        # Validate a delivery containing expired products must raise a confirmation wizard.
        self.assertNotEqual(res, True)
        self.assertEqual(res['res_model'], 'expiry.picking.confirmation')

    def test_edit_removal_date_in_inventory_mode(self):
        """ Try to edit removal_date with the inventory mode.
        """
        user_group_stock_manager = self.env.ref('stock.group_stock_manager')
        self.demo_user = mail_new_test_user(
            self.env,
            name='Demo user',
            login='userdemo',
            email='d.d@example.com',
            groups='stock.group_stock_manager',
        )
        lot_form = Form(self.LotObj)
        lot_form.name = 'LOT001'
        lot_form.product_id = self.apple_product
        lot_form.company_id = self.env.company
        apple_lot = lot_form.save()

        quant = self.StockQuantObj.with_context(inventory_mode=True).create({
            'product_id': self.apple_product.id,
            'location_id': self.stock_location,
            'quantity': 10,
            'lot_id': apple_lot.id,
        })
        # Try to write on quant with inventory mode
        new_date = datetime.today() + timedelta(days=15)
        quant.with_user(self.demo_user).with_context(inventory_mode=True).write({'removal_date': new_date})
        self.assertEqual(quant.removal_date, new_date)

    def test_apply_lot_date_on_sml(self):
        """
        When assigning a lot to a SML, if the lot has an expiration date,
        the latter should be applied on the SML
        """
        exp_date = fields.Datetime.today() + relativedelta(days=15)

        lot = self.env['stock.production.lot'].create({
            'name': 'Lot 1',
            'product_id': self.apple_product.id,
            'expiration_date': fields.Datetime.to_string(exp_date),
            'company_id': self.env.company.id,
        })

        sml = self.env['stock.move.line'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'product_id': self.apple_product.id,
            'qty_done': 3,
            'product_uom_id': self.apple_product.uom_id.id,
            'lot_id': lot.id,
            'company_id': self.env.company.id,
        })

        self.assertEqual(sml.expiration_date, exp_date)

        exp_date = exp_date + relativedelta(days=10)
        lot.expiration_date = exp_date
        self.assertEqual(sml.expiration_date, exp_date)

    def test_apply_lot_without_date_on_sml(self):
        """
        When assigning a lot to a SML, if the lot has no expiration date,
        dates on lot and SML should be correctly set
        """
        #create lot without expiration date
        lot = self.env['stock.production.lot'].create({
            'name': 'Lot 1',
            'product_id': self.apple_product.id,
            'company_id': self.env.company.id,
        })

        sml = self.env['stock.move.line'].create({
            'location_id': self.supplier_location,
            'location_dest_id': self.stock_location,
            'product_id': self.apple_product.id,
            'qty_done': 3,
            'product_uom_id': self.apple_product.uom_id.id,
            'lot_id': lot.id,
            'company_id': self.env.company.id,
        })
        today_date = datetime.today()
        time_gap = timedelta(seconds=10)
        exp_date = today_date + timedelta(days=self.apple_product.expiration_time)

        self.assertAlmostEqual(sml.expiration_date, exp_date, delta=time_gap)

        self.assertAlmostEqual(
            lot.expiration_date, exp_date, delta=time_gap)
        self.assertAlmostEqual(
            lot.use_date, exp_date - timedelta(days=self.apple_product.use_time), delta=time_gap)
        self.assertAlmostEqual(
            lot.removal_date, exp_date - timedelta(days=self.apple_product.removal_time), delta=time_gap)
        self.assertAlmostEqual(
            lot.alert_date, exp_date - timedelta(days=self.apple_product.alert_time), delta=time_gap)

    def test_apply_same_date_on_expiry_fields(self):
        expiration_time = 10
        self.apple_product.write({
            'expiration_time': expiration_time,
            'use_time': 0,
            'removal_time': 0,
            'alert_time': 0,
        })

        lot = self.env['stock.production.lot'].create({
            'product_id': self.apple_product.id,
            'company_id': self.env.company.id,
        })

        delta = timedelta(seconds=10)
        expiration_date = datetime.today() + timedelta(days=expiration_time)
        err_msg = "The time on the product is set to 0, it means that the corresponding date should be the same as the expiration one"
        self.assertAlmostEqual(lot.expiration_date, expiration_date, delta=delta)
        self.assertAlmostEqual(lot.use_date, expiration_date, delta=delta, msg=err_msg)
        self.assertAlmostEqual(lot.removal_date, expiration_date, delta=delta, msg=err_msg)
        self.assertAlmostEqual(lot.alert_date, expiration_date, delta=delta, msg=err_msg)
