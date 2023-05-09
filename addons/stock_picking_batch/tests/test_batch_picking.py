# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


class TestBatchPicking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """ Create a picking batch with two pickings from stock to customer """
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.picking_type_out = cls.env['ir.model.data']._xmlid_to_res_id('stock.picking_type_out')
        cls.env['stock.picking.type'].browse(cls.picking_type_out).reservation_method = 'manual'
        cls.productA = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.productB = cls.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

        cls.client_1 = cls.env['res.partner'].create({'name': 'Client 1'})
        cls.picking_client_1 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'partner_id': cls.client_1.id,
            'company_id': cls.env.company.id,
        })

        cls.env['stock.move'].create({
            'name': cls.productA.name,
            'product_id': cls.productA.id,
            'product_uom_qty': 10,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking_client_1.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.client_2 = cls.env['res.partner'].create({'name': 'Client 2'})
        cls.picking_client_2 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'partner_id': cls.client_2.id,
            'company_id': cls.env.company.id,
        })

        cls.env['stock.move'].create({
            'name': cls.productB.name,
            'product_id': cls.productB.id,
            'product_uom_qty': 10,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking_client_2.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.picking_client_3 = cls.env['stock.picking'].create({
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': cls.picking_type_out,
            'company_id': cls.env.company.id,
        })

        cls.env['stock.move'].create({
            'name': cls.productB.name,
            'product_id': cls.productB.id,
            'product_uom_qty': 10,
            'product_uom': cls.productA.uom_id.id,
            'picking_id': cls.picking_client_3.id,
            'location_id': cls.stock_location.id,
            'location_dest_id': cls.customer_location.id,
        })

        cls.batch = cls.env['stock.picking.batch'].create({
            'name': 'Batch 1',
            'company_id': cls.env.company.id,
            'picking_ids': [(4, cls.picking_client_1.id), (4, cls.picking_client_2.id)]
        })

    def test_batch_scheduled_date(self):
        """ Test to make sure the correct scheduled date is set for both a batch and its pickings.
        Setting a batch's scheduled date manually has different behavior from when it is automatically
        set/updated via compute.
        """

        now = datetime.now().replace(microsecond=0)
        self.batch.scheduled_date = now

        # TODO: this test cannot currently handle the onchange scheduled_date logic because of test form
        # view not handling the M2M widget assigned to picking_ids (O2M). Hopefully if this changes then
        # commented parts of this test can be used later.


        # manually set batch scheduled date => picking's scheduled dates auto update to match (onchange logic test)
        # with Form(self.batch) as batch_form:
            # batch_form.scheduled_date = now - timedelta(days=1)
            # batch_form.save()
        # self.assertEqual(self.batch.scheduled_date, self.picking_client_1.scheduled_date)
        # self.assertEqual(self.batch.scheduled_date, self.picking_client_2.scheduled_date)

        picking1_scheduled_date = now - timedelta(days=2)
        picking2_scheduled_date = now - timedelta(days=3)
        picking3_scheduled_date = now - timedelta(days=4)

        # manually update picking scheduled dates => batch's scheduled date auto update to match lowest value
        self.picking_client_1.scheduled_date = picking1_scheduled_date
        self.picking_client_2.scheduled_date = picking2_scheduled_date
        self.assertEqual(self.batch.scheduled_date, self.picking_client_2.scheduled_date)
        # but individual pickings keep original scheduled dates
        self.assertEqual(self.picking_client_1.scheduled_date, picking1_scheduled_date)
        self.assertEqual(self.picking_client_2.scheduled_date, picking2_scheduled_date)

        # add a new picking with an earlier scheduled date => batch's scheduled date should auto-update
        self.picking_client_3.scheduled_date = picking3_scheduled_date
        self.batch.write({'picking_ids': [(4, self.picking_client_3.id)]})
        self.assertEqual(self.batch.scheduled_date, self.picking_client_3.scheduled_date)

        # remove that picking and batch scheduled date should auto-update to next min date
        self.batch.write({'picking_ids': [(3, self.picking_client_3.id)]})
        self.assertEqual(self.batch.scheduled_date, self.picking_client_2.scheduled_date)

        # directly add new picking with an earlier scheduled date => batch's scheduled date auto updates to match,
        # but existing pickings do not (onchange logic test)
        # with Form(self.batch) as batch_form:
        #     batch_form.picking_ids.add(self.picking_client_3)
        #     batch_form.save()
        # # individual pickings keep original scheduled dates
        self.assertEqual(self.picking_client_1.scheduled_date, picking1_scheduled_date)
        self.assertEqual(self.picking_client_2.scheduled_date, picking2_scheduled_date)
        # self.assertEqual(self.batch.scheduled_date, self.picking_client_3.scheduled_date)
        # self.batch.write({'picking_ids': [(3, self.picking_client_3.id)]})

        # cancelling batch should auto-remove all pickings => scheduled_date should default to none
        self.batch.action_cancel()
        self.assertEqual(len(self.batch.picking_ids), 0)
        self.assertEqual(self.batch.scheduled_date, False)

    def test_simple_batch_with_manual_qty_done(self):
        """ Test a simple batch picking with all quantity for picking available.
        The user set all the quantity_done on picking manually and no wizard are used.
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # Confirm batch, pickings should not be automatically assigned.
        self.batch.action_confirm()
        self.assertEqual(self.picking_client_1.state, 'confirmed', 'Picking 1 should be confirmed')
        self.assertEqual(self.picking_client_2.state, 'confirmed', 'Picking 2 should be confirmed')
        # Ask to assign, so pickings should be assigned now.
        self.batch.action_assign()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        self.picking_client_1.move_ids.quantity_done = 10
        self.picking_client_2.move_ids.quantity_done = 10
        self.batch.action_done()

        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_2.state, 'done', 'Picking 2 should be done')

        quant_A = self.env['stock.quant']._gather(self.productA, self.stock_location)
        quant_B = self.env['stock.quant']._gather(self.productB, self.stock_location)

        # ensure that quantity for picking has been moved
        self.assertFalse(sum(quant_A.mapped('quantity')))
        self.assertFalse(sum(quant_B.mapped('quantity')))

        # ensure that batch cannot be deleted now that it is done
        with self.assertRaises(UserError):
            self.batch.unlink()

    def test_simple_batch_with_wizard(self):
        """ Test a simple batch picking with all quantity for picking available.
        The user use the wizard in order to complete automatically the quantity_done to
        the initial demand (or reserved quantity in this test).
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # Confirm batch, pickings should not be automatically assigned.
        self.batch.action_confirm()
        self.assertEqual(self.picking_client_1.state, 'confirmed', 'Picking 1 should be confirmed')
        self.assertEqual(self.picking_client_2.state, 'confirmed', 'Picking 2 should be confirmed')
        # Ask to assign, so pickings should be assigned now.
        self.batch.action_assign()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        # There should be a wizard asking to process picking without quantity done
        immediate_transfer_wizard_dict = self.batch.action_done()
        self.assertTrue(immediate_transfer_wizard_dict)
        immediate_transfer_wizard = Form(self.env[(immediate_transfer_wizard_dict.get('res_model'))].with_context(immediate_transfer_wizard_dict['context'])).save()
        self.assertEqual(len(immediate_transfer_wizard.pick_ids), 2)
        immediate_transfer_wizard.process()

        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_2.state, 'done', 'Picking 2 should be done')

        quant_A = self.env['stock.quant']._gather(self.productA, self.stock_location)
        quant_B = self.env['stock.quant']._gather(self.productB, self.stock_location)

        # ensure that quantity for picking has been moved
        self.assertFalse(sum(quant_A.mapped('quantity')))
        self.assertFalse(sum(quant_B.mapped('quantity')))

    def test_batch_with_backorder_wizard(self):
        """ Test a simple batch picking with all quantities fully available but only one fully
        processed. The user will set by himself the quantity reserved for each picking and
        run the picking batch. There should be a wizard asking for a backorder.
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # Confirm batch, pickings should not be automatically assigned.
        self.batch.action_confirm()
        self.assertEqual(self.picking_client_1.state, 'confirmed', 'Picking 1 should be confirmed')
        self.assertEqual(self.picking_client_2.state, 'confirmed', 'Picking 2 should be confirmed')
        # Ask to assign, so pickings should be assigned now.
        self.batch.action_assign()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        self.picking_client_1.move_ids.quantity_done = 6
        self.picking_client_2.move_ids.quantity_done = 10

        # There should be a wizard asking to process picking without quantity done
        back_order_wizard_dict = self.batch.action_done()
        self.assertTrue(back_order_wizard_dict)
        back_order_wizard = Form(self.env[(back_order_wizard_dict.get('res_model'))].with_context(back_order_wizard_dict['context'])).save()
        self.assertEqual(len(back_order_wizard.pick_ids), 1)
        back_order_wizard.process()

        self.assertEqual(self.picking_client_2.state, 'done', 'Picking 2 should be done')
        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_1.move_ids.product_uom_qty, 6, 'initial demand should be 6 after picking split')
        self.assertTrue(self.env['stock.picking'].search([('backorder_id', '=', self.picking_client_1.id)]), 'no back order created')

        quant_A = self.env['stock.quant']._gather(self.productA, self.stock_location)
        quant_B = self.env['stock.quant']._gather(self.productB, self.stock_location)

        # ensure that quantity for picking has been moved
        self.assertEqual(sum(quant_A.mapped('quantity')), 4)
        self.assertFalse(sum(quant_B.mapped('quantity')))

    def test_batch_without_backorder_wizard(self):
        """ Test a simple batch picking with only one quantity fully available.
        The user will set by himself the quantity reserved for each picking and
        run the picking batch. A backorder should be automatically created.
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 5.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # Confirm batch, pickings should not be automatically assigned.
        self.batch.action_confirm()
        self.assertEqual(self.picking_client_1.state, 'confirmed', 'Picking 1 should be confirmed')
        self.assertEqual(self.picking_client_2.state, 'confirmed', 'Picking 2 should be confirmed')
        # Ask to assign, so pickings should be assigned now.
        self.batch.action_assign()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        self.picking_client_1.move_ids.quantity_done = 5
        self.picking_client_2.move_ids.quantity_done = 10
        self.batch.action_done()

        # Checks a backorder was created for `picking_client_1`.
        backorder = self.env['stock.picking'].search([('backorder_id', 'in', self.batch.picking_ids.ids)])
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder.backorder_id.id, self.picking_client_1.id)

        self.assertEqual(self.picking_client_2.state, 'done', 'Picking 2 should be done')
        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_1.move_ids.product_uom_qty, 5, 'initial demand should be 5 after picking split')
        self.assertTrue(self.env['stock.picking'].search([('backorder_id', '=', self.picking_client_1.id)]), 'no back order created')

        quant_A = self.env['stock.quant']._gather(self.productA, self.stock_location)
        quant_B = self.env['stock.quant']._gather(self.productB, self.stock_location)

        # ensure that quantity for picking has been moved
        self.assertFalse(sum(quant_A.mapped('quantity')))
        self.assertFalse(sum(quant_B.mapped('quantity')))

    def test_batch_with_immediate_transfer_and_backorder(self):
        """ Test a simple batch picking with only one product fully available.
        Everything should be automatically. The immediate transfer wizard should asking to set
        quantity_done to reserved quantity. A backorder should be created without wizard as the
        reserved quantity was fully processed.
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 5.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # Confirm batch, pickings should not be automatically assigned.
        self.batch.action_confirm()
        self.assertEqual(self.picking_client_1.state, 'confirmed', 'Picking 1 should be confirmed')
        self.assertEqual(self.picking_client_2.state, 'confirmed', 'Picking 2 should be confirmed')
        # Ask to assign, so pickings should be assigned now.
        self.batch.action_assign()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        # There should be a wizard asking to process picking without quantity done
        immediate_transfer_wizard_dict = self.batch.action_done()
        self.assertTrue(immediate_transfer_wizard_dict)
        immediate_transfer_wizard = Form(self.env[(immediate_transfer_wizard_dict.get('res_model'))].with_context(immediate_transfer_wizard_dict['context'])).save()
        self.assertEqual(len(immediate_transfer_wizard.pick_ids), 2)
        immediate_transfer_wizard.process()

        # Checks a backorder was created for `picking_client_1`.
        backorder = self.env['stock.picking'].search([('backorder_id', 'in', self.batch.picking_ids.ids)])
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder.backorder_id.id, self.picking_client_1.id)

        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_1.move_ids.product_uom_qty, 5, 'initial demand should be 5 after picking split')
        self.assertTrue(self.env['stock.picking'].search([('backorder_id', '=', self.picking_client_1.id)]), 'no back order created')

        quant_A = self.env['stock.quant']._gather(self.productA, self.stock_location)
        quant_B = self.env['stock.quant']._gather(self.productB, self.stock_location)

        # ensure that quantity for picking has been moved
        self.assertFalse(sum(quant_A.mapped('quantity')))
        self.assertFalse(sum(quant_B.mapped('quantity')))

    def test_batch_with_immediate_transfer_and_backorder_wizard_with_manual_operations(self):
        """ Test a simple batch picking with a quantity not fully processed.
        The user set the quantity done only for the first picking.
        The test should run the immediate transfer for the second picking and then
        the backorder wizard for the first picking.
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # Confirm batch, pickings should not be automatically assigned.
        self.batch.action_confirm()
        self.assertEqual(self.picking_client_1.state, 'confirmed', 'Picking 1 should be confirmed')
        self.assertEqual(self.picking_client_2.state, 'confirmed', 'Picking 2 should be confirmed')
        # Ask to assign, so pickings should be assigned now.
        self.batch.action_assign()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        self.picking_client_1.move_ids.quantity_done = 6
        # There should be a wizard asking to make a backorder
        back_order_wizard_dict = self.batch.action_done()
        self.assertTrue(back_order_wizard_dict)
        self.assertEqual(back_order_wizard_dict.get('res_model'), 'stock.backorder.confirmation')
        back_order_wizard = Form(self.env[(back_order_wizard_dict.get('res_model'))].with_context(back_order_wizard_dict['context'])).save()
        # Empty pickings are excluded from the validation process, to be removed from the batch afterwards.
        self.assertEqual(len(back_order_wizard.pick_ids), 1)
        back_order_wizard.process()

        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_1.move_ids.product_uom_qty, 6, 'initial demand should be 5 after picking split')
        self.assertFalse(self.picking_client_2.batch_id)

    def test_put_in_pack(self):
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # Confirm batch, pickings should not be automatically assigned.
        self.batch.action_confirm()
        self.assertEqual(self.picking_client_1.state, 'confirmed', 'Picking 1 should be confirmed')
        self.assertEqual(self.picking_client_2.state, 'confirmed', 'Picking 2 should be confirmed')
        # Ask to assign, so pickings should be assigned now.
        self.batch.action_assign()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        # only do part of pickings + assign different destinations + try to pack (should get wizard to correct destination)
        self.batch.move_line_ids.qty_done = 5
        self.batch.move_line_ids[0].location_dest_id = self.stock_location.id
        wizard_values = self.batch.action_put_in_pack()
        wizard = self.env[(wizard_values.get('res_model'))].browse(wizard_values.get('res_id'))
        wizard.location_dest_id = self.customer_location.id
        package = wizard.action_done()

        # a new package is made and done quantities should be in same package
        self.assertTrue(package)
        done_qty_move_lines = self.batch.move_line_ids.filtered(lambda ml: ml.qty_done == 5)
        self.assertEqual(done_qty_move_lines[0].result_package_id.id, package.id)
        self.assertEqual(done_qty_move_lines[1].result_package_id.id, package.id)

        # not done quantities should be split into separate lines
        self.assertEqual(len(self.batch.move_line_ids), 4)

        # confirm w/ backorder
        back_order_wizard_dict = self.batch.action_done()
        self.assertTrue(back_order_wizard_dict)
        back_order_wizard = Form(self.env[(back_order_wizard_dict.get('res_model'))].with_context(back_order_wizard_dict['context'])).save()
        self.assertEqual(len(back_order_wizard.pick_ids), 2)
        back_order_wizard.process()

        # final package location should be correctly set based on wizard
        self.assertEqual(package.location_id.id, self.customer_location.id)

    def test_auto_batch(self):
        """ Test a simple auto-batch scenario with new picking type to avoid conflicts with existing picking types.
        The pickings look like this:
        Picking_out_1           Picking_out_2           Picking_out_3
            Partner_1                Partner_2                Partner_1

        So as the picking type is defined to batch automatically by partner, Picking 1&3 should be batched at their confirmation, while Picking2 isn't.
        """
        # Create picking type to avoid conflicts with existing pickings with auto-batch enabled grouping by partner.
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        type_special_out = self.env['stock.picking.type'].create({
            'name': 'Special Delivery',
            'sequence_code': 'SPECOUT',
            'code': 'outgoing',
            'company_id': self.env.company.id,
            'warehouse_id': warehouse.id,
            'auto_batch': True,
            'batch_group_by_partner': True,
        })
        partner_1 = self.env['res.partner'].create({
            'name': 'Partner 1'
        })
        partner_2 = self.env['res.partner'].create({
            'name': 'Partner 2'
        })
        # Pickings need to be in 'ready' state to be auto-batchable
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 20)

        # Create the pickings that will be confirmed and batched afterwards
        picking_out_1 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': type_special_out.id,
            'company_id': self.env.company.id,
            'partner_id': partner_1.id
        })
        self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_out_1.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        picking_out_2 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': type_special_out.id,
            'company_id': self.env.company.id,
            'partner_id': partner_2.id
        })
        self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 10,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_out_2.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        picking_out_3 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': type_special_out.id,
            'company_id': self.env.company.id,
            'partner_id': partner_1.id
        })
        self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 10,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_out_3.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        all_pickings = picking_out_1 | picking_out_2 | picking_out_3
        # No pickings should have any batch before confirmation
        self.assertFalse(all_pickings.batch_id)

        all_pickings.action_confirm()
        # Now Picking 1 and 3 should be batched together, while Picking 2 is still in no batch.
        self.assertTrue(picking_out_1.batch_id)
        self.assertTrue(picking_out_3.batch_id)
        self.assertEqual(picking_out_1.batch_id.id, picking_out_3.batch_id.id)
        self.assertFalse(picking_out_2.batch_id)
        # If Picking 1 is validated without Picking 3, Picking 1 should be removed from the batch
        picking_out_1.move_ids.quantity_done = 10
        picking_out_1.button_validate()
        self.assertFalse(picking_out_1.batch_id)
        self.assertEqual(len(picking_out_3.batch_id.picking_ids), 1)

    def test_auto_batch_02(self):
        """ Test that the auto batch works correctly in internal transfers
            when they are created from an order point:
            * WH1: 1 steps outgoing transfers:
                - Delivery orders: auto batch - source location
            * WH2: 3 steps incoming transfers, ressuply from WH1
                - internal transfert/ WH2 : auto batch - destination location
            * orderpoint:
                - Product A - Location: WH2 - Route: WH2/supply from WH1 - procurement: P1 - min_qty: 1
                - Product B - Location: WH2 - Route: WH2/supply from >H1 - procurement: P2 - min_qty: 1

            * Result: 8 pickings and 4 batchs
        """
        warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'WH 1',
            'code': 'WH1',
            'company_id': self.env.company.id,
        })
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'WH 2',
            'code': 'WH2',
            'company_id': warehouse_1.company_id.id,
            'resupply_wh_ids': [(6, 0, [warehouse_1.id])],
            'reception_steps': 'three_steps',
        })
        warehouse_1.out_type_id.write({
            'reservation_method': 'at_confirm',
            'auto_batch': True,
            'batch_group_by_src_loc': True,
        })
        warehouse_2.int_type_id.write({
            'auto_batch': True,
            'batch_group_by_dest_loc': True,
        })
        self.env['stock.quant']._update_available_quantity(self.productA, warehouse_1.lot_stock_id, 10)
        self.env['stock.quant']._update_available_quantity(self.productB, warehouse_1.lot_stock_id, 10)
        procurement_1 = self.env['procurement.group'].create({
            'move_type': 'direct',
            'partner_id': self.client_1.id
        })
        procurement_2 = self.env['procurement.group'].create({
            'move_type': 'direct',
            'partner_id': self.client_1.id
        })
        op1 = self.env['stock.warehouse.orderpoint'].create({
            'name': 'Product A',
            'location_id': warehouse_2.lot_stock_id.id,
            'product_id': self.productA.id,
            'product_min_qty': 1,
            'product_max_qty': 1,
            'group_id': procurement_1.id,
            'route_id': warehouse_2.resupply_route_ids[0].id,
        })
        op2 = self.env['stock.warehouse.orderpoint'].create({
            'name': 'Product B',
            'location_id': warehouse_2.lot_stock_id.id,
            'product_id': self.productB.id,
            'product_min_qty': 1,
            'product_max_qty': 1,
            'group_id': procurement_2.id,
            'route_id': warehouse_2.resupply_route_ids[0].id,
        })
        self.productA.route_ids = warehouse_2.resupply_route_ids
        self.productB.route_ids = warehouse_2.resupply_route_ids
        (op1 | op2)._procure_orderpoint_confirm()
        # Only delivery pickings from WH1/Stock -> Inter-warehouse should be 'ready', so only one batch
        current_batch = procurement_1.stock_move_ids.picking_id.batch_id
        self.assertNotEqual(current_batch.id, False)
        self.assertEqual(len(procurement_1.stock_move_ids.picking_id.batch_id), 1)
        self.assertEqual(procurement_1.stock_move_ids.picking_id.filtered(lambda p: p.picking_type_code == 'outgoing').batch_id,
                         procurement_2.stock_move_ids.picking_id.filtered(lambda p: p.picking_type_code == 'outgoing').batch_id)

        # Validate the batch so the next round of pickings become 'ready' -> Incoming pickings to Inter-warehouse -> WH2/Input
        current_batch.move_ids.write({'quantity_done': 1})
        current_batch.action_done()
        done_batches = current_batch
        self.assertEqual(len(procurement_1.stock_move_ids.picking_id.batch_id), 2)
        self.assertEqual(procurement_1.stock_move_ids.picking_id.filtered(lambda p: p.picking_type_code == 'incoming').batch_id,
                         procurement_2.stock_move_ids.picking_id.filtered(lambda p: p.picking_type_code == 'incoming').batch_id)

        # Validate the batch so the next round of pickings become 'ready' -> Internal pickings : WH2/Input -> WH2/Quality Control
        current_batch = procurement_1.stock_move_ids.picking_id.batch_id - done_batches
        current_batch.move_ids.write({'quantity_done': 1})
        current_batch.action_done()
        done_batches += current_batch
        self.assertEqual(len(procurement_1.stock_move_ids.picking_id.batch_id), 3)
        self.assertEqual(procurement_1.stock_move_ids.picking_id.filtered(lambda p: p.picking_type_code == 'internal' and p.location_id == warehouse_2.in_type_id).batch_id,
                         procurement_2.stock_move_ids.picking_id.filtered(lambda p: p.picking_type_code == 'internal' and p.location_id == warehouse_2.in_type_id).batch_id)

        # Validate the batch so the next round of pickings become 'ready' -> Internal pickings : WH2/Input -> WH2/Quality Control
        current_batch = procurement_1.stock_move_ids.picking_id.batch_id - done_batches
        current_batch.move_ids.write({'quantity_done': 1})
        current_batch.action_done()
        self.assertEqual(len(procurement_1.stock_move_ids.picking_id.batch_id), 4)
        self.assertEqual(procurement_1.stock_move_ids.picking_id.filtered(lambda p: p.picking_type_code == 'internal' and p.location_dest_id == warehouse_2.lot_stock_id).batch_id,
                         procurement_2.stock_move_ids.picking_id.filtered(lambda p: p.picking_type_code == 'internal' and p.location_dest_id == warehouse_2.lot_stock_id).batch_id)

    def test_remove_all_transfers_from_confirmed_batch(self):
        """
            Check that the batch is canceled when all transfers are deleted
        """
        self.batch.action_confirm()
        self.assertEqual(self.batch.state, 'in_progress', 'Batch Transfers should be in progress.')
        self.batch.write({'picking_ids': [[5, 0, 0]]})
        self.assertEqual(self.batch.state, 'cancel', 'Batch Transfers should be cancelled when there are no transfers.')


@tagged('-at_install', 'post_install')
class TestBatchPicking02(TransactionCase):

    def setUp(self):
        super().setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.picking_type_internal = self.env.ref('stock.picking_type_internal')
        self.productA = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.productB = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def test_same_package_several_pickings(self):
        """
        A batch with two transfers, source and destination are the same. The
        first picking contains 3 x P, the second one 7 x P. The 10 P are in a
        package. It should be possible to transfer the whole package across the
        two pickings
        """
        package = self.env['stock.quant.package'].create({
            'name': 'superpackage',
        })

        loc1, loc2 = self.stock_location.child_ids
        self.env['stock.quant']._update_available_quantity(self.productA, loc1, 10, package_id=package)

        pickings = self.env['stock.picking'].create([{
            'location_id': loc1.id,
            'location_dest_id': loc2.id,
            'picking_type_id': self.picking_type_internal.id,
            'move_ids': [(0, 0, {
                'name': 'test_put_in_pack_from_multiple_pages',
                'location_id': loc1.id,
                'location_dest_id': loc2.id,
                'product_id': self.productA.id,
                'product_uom': self.productA.uom_id.id,
                'product_uom_qty': qty,
            })]
        } for qty in (3, 7)])
        pickings.action_confirm()
        pickings.action_assign()

        batch_form = Form(self.env['stock.picking.batch'])
        batch_form.picking_ids.add(pickings[0])
        batch_form.picking_ids.add(pickings[1])
        batch = batch_form.save()
        batch.action_confirm()

        pickings.move_line_ids[0].qty_done = 3
        pickings.move_line_ids[1].qty_done = 7
        pickings.move_line_ids.result_package_id = package

        batch.action_done()
        self.assertRecordValues(pickings.move_ids, [
            {'state': 'done', 'quantity_done': 3},
            {'state': 'done', 'quantity_done': 7},
        ])
        self.assertEqual(pickings.move_line_ids.result_package_id, package)


    def test_batch_validation_without_backorder(self):
        loc1, loc2 = self.stock_location.child_ids
        self.env['stock.quant']._update_available_quantity(self.productA, loc1, 10)
        self.env['stock.quant']._update_available_quantity(self.productB, loc1, 10)
        picking_1 = self.env['stock.picking'].create({
            'location_id': loc1.id,
            'location_dest_id': loc2.id,
            'picking_type_id': self.picking_type_internal.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': picking_1.id,
            'location_id': loc1.id,
            'location_dest_id': loc2.id,
        })

        picking_2 = self.env['stock.picking'].create({
            'location_id': loc1.id,
            'location_dest_id': loc2.id,
            'picking_type_id': self.picking_type_internal.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 5,
            'product_uom': self.productB.uom_id.id,
            'picking_id': picking_2.id,
            'location_id': loc1.id,
            'location_dest_id': loc2.id,
        })
        (picking_1 | picking_2).action_confirm()
        (picking_1 | picking_2).action_assign()
        picking_2.move_ids.move_line_ids.write({'qty_done': 1})

        batch = self.env['stock.picking.batch'].create({
            'name': 'Batch 1',
            'company_id': self.env.company.id,
            'picking_ids': [(4, picking_1.id), (4, picking_2.id)]
        })
        batch.action_confirm()
        action = batch.action_done()
        Form(self.env[action['res_model']].with_context(action['context'])).save().process_cancel_backorder()
        self.assertEqual(batch.state, 'done')
