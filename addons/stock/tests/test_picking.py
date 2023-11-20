from odoo.tests import common, Form
from odoo.exceptions import UserError

class TestPicking(common.TransactionCase):

    def test_00_no_duplicate_sequence_code(self):
        stock_location = self.env.ref('stock.stock_location_stock')
        operation_type_1 = self.env['stock.picking.type'].create({
            'name':'test 1',
            'code': 'internal',
            'default_location_src_id':stock_location.id,
            'default_location_dest_id':stock_location.id,
            'sequence_code':'testpicking'
        })
        with self.assertRaises(UserError) as er:
            self.env['stock.picking.type'].create({
                'name':'test 2',
                'code': 'internal',
                'default_location_src_id':stock_location.id,
                'default_location_dest_id':stock_location.id,
                'sequence_code':'testpicking'
            })
        self.assertEqual(
            er.exception.args[0], f'Sequences {operation_type_1.sequence_id.name} already exist.')

    def test_return_picking_validation_with_tracked_product(self):
        """
        Test That return picking can be validated when the product is tracked by serial number
        - Create an incoming immediate transfer with a tracked picking, validate it
        - Create a return and validate it
        """
        in_picking_type = self.env.ref('stock.picking_type_in')
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        stock_location = self.env.ref('stock.stock_location_stock')
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'tracking': 'serial',
        })
        sn_1, sn_2 = [self.env['stock.lot'].create({
            'name': str(i),
            'product_id': product.id,
        }) for i in range(2)]
        # create an immediate transfer
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': in_picking_type.id,
            'location_id': supplier_location.id,
            'location_dest_id': stock_location.id,
            'immediate_transfer': True,
        })
        move = self.env['stock.move'].create({
                'picking_id': picking_in.id,
                'name': product.name,
                'product_id': product.id,
                'quantity_done': 2,
                'product_uom': product.uom_id.id,
                'location_id': supplier_location.id,
                'location_dest_id': stock_location.id,
        })
        self.assertEqual(picking_in.state, 'assigned')
        move.move_line_ids[0].write({'lot_id': sn_1.id, 'qty_done': 1})
        move.move_line_ids[1].write({'lot_id': sn_2.id, 'qty_done': 1})
        picking_in.button_validate()
        # create a return picking
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking_in.ids, active_id=picking_in.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        self.assertEqual(return_picking.state, 'assigned')
        wiz = return_picking.button_validate()
        wiz = Form(self.env['stock.immediate.transfer'].with_context(wiz['context'])).save().process()
        self.assertEqual(return_picking.move_ids.quantity_done, 2)
        self.assertEqual(return_picking.state, 'done')
