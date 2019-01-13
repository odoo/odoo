from odoo.tests.common import TransactionCase


class TestBatchPicking(TransactionCase):

    def setUp(self):
        """ Create a picking batch with two pickings from stock to customer """
        super(TestBatchPicking, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.partner_delta_id = self.env['ir.model.data'].xmlid_to_res_id('base.res_partner_4')
        self.picking_type_out = self.env['ir.model.data'].xmlid_to_res_id('stock.picking_type_out')
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
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
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
            'partner_id': self.partner_delta_id,
            'picking_type_id': self.picking_type_out,
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

        self.batch = self.env['stock.picking.batch'].create({
            'name': 'Batch 1',
            'picking_ids': [(4, self.picking_client_1.id), (4, self.picking_client_2.id)]
        })

    def test_simple_batch_with_manual_qty_done(self):
        """ Test a simple batch picking with all quantity for picking available.
        The user set all the quantity_done on picking manually and no wizard are used.
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # confirm batch, picking should be assigned
        self.batch.confirm_picking()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be reserved')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be reserved')

        self.picking_client_1.move_lines.quantity_done = 10
        self.picking_client_2.move_lines.quantity_done = 10
        self.batch.done()

        self.assertEqual(self.picking_client_1.state, 'done', 'Picking 1 should be done')
        self.assertEqual(self.picking_client_2.state, 'done', 'Picking 2 should be done')

        quant_A = self.env['stock.quant']._gather(self.productA, self.stock_location)
        quant_B = self.env['stock.quant']._gather(self.productB, self.stock_location)

        # ensure that quantity for picking has been moved
        self.assertFalse(sum(quant_A.mapped('quantity')))
        self.assertFalse(sum(quant_B.mapped('quantity')))

    def test_simple_batch_with_wizard(self):
        """ Test a simple batch picking with all quantity for picking available.
        The user use the wizard in order to complete automatically the quantity_done to
        the initial demand (or reserved quantity in this test).
        """
        self.env['stock.quant']._update_available_quantity(self.productA, self.stock_location, 10.0)
        self.env['stock.quant']._update_available_quantity(self.productB, self.stock_location, 10.0)

        # confirm batch, picking should be assigned
        self.batch.confirm_picking()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be reserved')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be reserved')

        # There should be a wizard asking to process picking without quantity done
        immediate_transfer_wizard_dict = self.batch.done()
        self.assertTrue(immediate_transfer_wizard_dict)
        immediate_transfer_wizard = self.env[(immediate_transfer_wizard_dict.get('res_model'))].browse(immediate_transfer_wizard_dict.get('res_id'))
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

        # confirm batch, picking should be assigned
        self.batch.confirm_picking()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        self.picking_client_1.move_lines.quantity_done = 5
        self.picking_client_2.move_lines.quantity_done = 10

        # There should be a wizard asking to process picking without quantity done
        back_order_wizard_dict = self.batch.done()
        self.assertTrue(back_order_wizard_dict)
        back_order_wizard = self.env[(back_order_wizard_dict.get('res_model'))].browse(back_order_wizard_dict.get('res_id'))
        self.assertEqual(len(back_order_wizard.pick_ids), 1)
        self.assertEqual(self.picking_client_2.state, 'done', 'Picking 2 should be done')
        back_order_wizard.process()

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

        # confirm batch, picking should be assigned
        self.batch.confirm_picking()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        # There should be a wizard asking to process picking without quantity done
        immediate_transfer_wizard_dict = self.batch.done()
        self.assertTrue(immediate_transfer_wizard_dict)
        immediate_transfer_wizard = self.env[(immediate_transfer_wizard_dict.get('res_model'))].browse(immediate_transfer_wizard_dict.get('res_id'))
        self.assertEqual(len(immediate_transfer_wizard.pick_ids), 2)
        back_order_wizard_dict = immediate_transfer_wizard.process()
        self.assertTrue(back_order_wizard_dict)
        back_order_wizard = self.env[(back_order_wizard_dict.get('res_model'))].browse(back_order_wizard_dict.get('res_id'))
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

        # confirm batch, picking should be assigned
        self.batch.confirm_picking()
        self.assertEqual(self.picking_client_1.state, 'assigned', 'Picking 1 should be ready')
        self.assertEqual(self.picking_client_2.state, 'assigned', 'Picking 2 should be ready')

        self.picking_client_1.move_lines.quantity_done = 5
        # There should be a wizard asking to process picking without quantity done
        immediate_transfer_wizard_dict = self.batch.done()
        self.assertTrue(immediate_transfer_wizard_dict)
        immediate_transfer_wizard = self.env[(immediate_transfer_wizard_dict.get('res_model'))].browse(immediate_transfer_wizard_dict.get('res_id'))
        self.assertEqual(len(immediate_transfer_wizard.pick_ids), 1)
        back_order_wizard_dict = immediate_transfer_wizard.process()
        self.assertTrue(back_order_wizard_dict)
        back_order_wizard = self.env[(back_order_wizard_dict.get('res_model'))].browse(back_order_wizard_dict.get('res_id'))
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
