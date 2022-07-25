# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestBatchPicking(TransactionCase):

    def setUp(self):
        """ Create a picking batch with two pickings from stock to customer """
        super(TestBatchPicking, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.picking_type_out = self.env['ir.model.data']._xmlid_to_res_id('stock.picking_type_out')
        self.env['stock.picking.type'].browse(self.picking_type_out).reservation_method = 'manual'
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

        self.picking_client_1 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out,
            'company_id': self.env.company.id,
        })

        self.env['stock.move'].create({
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking_client_1.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        self.picking_client_2 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out,
            'company_id': self.env.company.id,
        })

        self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking_client_2.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        self.picking_client_3 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out,
            'company_id': self.env.company.id,
        })

        self.env['stock.move'].create({
            'name': self.productB.name,
            'product_id': self.productB.id,
            'product_uom_qty': 10,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking_client_3.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })

        self.batch = self.env['stock.picking.batch'].create({
            'name': 'Batch 1',
            'company_id': self.env.company.id,
            'picking_ids': [(4, self.picking_client_1.id), (4, self.picking_client_2.id)]
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

        self.picking_client_1.move_lines.quantity_done = 10
        self.picking_client_2.move_lines.quantity_done = 10
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
        """ Test a simple batch picking with only one quantity fully available.
        The user will set by himself the quantity reserved for each picking and
        run the picking batch. There should be a wizard asking for a backorder.
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

        self.picking_client_1.move_lines.quantity_done = 5
        self.picking_client_2.move_lines.quantity_done = 10

        # There should be a wizard asking to process picking without quantity done
        back_order_wizard_dict = self.batch.action_done()
        self.assertTrue(back_order_wizard_dict)
        back_order_wizard = Form(self.env[(back_order_wizard_dict.get('res_model'))].with_context(back_order_wizard_dict['context'])).save()
        self.assertEqual(len(back_order_wizard.pick_ids), 1)
        back_order_wizard.process()

        self.assertEqual(self.picking_client_2.state, 'done', 'Picking 2 should be done')
        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_1.move_lines.product_uom_qty, 5, 'initial demand should be 5 after picking split')
        self.assertTrue(self.env['stock.picking'].search([('backorder_id', '=', self.picking_client_1.id)]), 'no back order created')

        quant_A = self.env['stock.quant']._gather(self.productA, self.stock_location)
        quant_B = self.env['stock.quant']._gather(self.productB, self.stock_location)

        # ensure that quantity for picking has been moved
        self.assertFalse(sum(quant_A.mapped('quantity')))
        self.assertFalse(sum(quant_B.mapped('quantity')))

    def test_batch_with_immediate_transfer_and_backorder_wizard(self):
        """ Test a simple batch picking with only one product fully available.
        Everything should be automatically. First one backorder in order to set quantity_done
        to reserved quantity. After a second wizard asking for a backorder for the quantity that
        has not been fully transfered.
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
        back_order_wizard_dict = immediate_transfer_wizard.process()
        self.assertTrue(back_order_wizard_dict)
        back_order_wizard = Form(self.env[(back_order_wizard_dict.get('res_model'))].with_context(back_order_wizard_dict['context'])).save()
        self.assertEqual(len(back_order_wizard.pick_ids), 1)
        back_order_wizard.process()

        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_1.move_lines.product_uom_qty, 5, 'initial demand should be 5 after picking split')
        self.assertTrue(self.env['stock.picking'].search([('backorder_id', '=', self.picking_client_1.id)]), 'no back order created')

        quant_A = self.env['stock.quant']._gather(self.productA, self.stock_location)
        quant_B = self.env['stock.quant']._gather(self.productB, self.stock_location)

        # ensure that quantity for picking has been moved
        self.assertFalse(sum(quant_A.mapped('quantity')))
        self.assertFalse(sum(quant_B.mapped('quantity')))

    def test_batch_with_immediate_transfer_and_backorder_wizard_with_manual_operations(self):
        """ Test a simple batch picking with only one quantity fully available.
        The user set the quantity done only for the partially available picking.
        The test should run the immediate transfer for the first picking and then
        the backorder wizard for the second picking.
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

        self.picking_client_1.move_lines.quantity_done = 5
        # There should be a wizard asking to make a backorder
        back_order_wizard_dict = self.batch.action_done()
        self.assertTrue(back_order_wizard_dict)
        self.assertEqual(back_order_wizard_dict.get('res_model'), 'stock.backorder.confirmation')
        back_order_wizard = Form(self.env[(back_order_wizard_dict.get('res_model'))].with_context(back_order_wizard_dict['context'])).save()
        self.assertEqual(len(back_order_wizard.pick_ids), 2)
        back_order_wizard.process()

        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_1.move_lines.product_uom_qty, 5, 'initial demand should be 5 after picking split')
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

    def test_remove_all_transfers_from_confirmed_batch(self):
        """
            Check that the batch is canceled when all transfers are deleted
        """
        self.batch.action_confirm()
        self.assertEqual(self.batch.state, 'in_progress', 'Batch Transfers should be in progress.')
        self.batch.write({'picking_ids': [[5, 0, 0]]})
        self.assertEqual(self.batch.state, 'cancel', 'Batch Transfers should be cancelled when there are no transfers.')
