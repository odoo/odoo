from odoo.tests import common
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

    def test_empty_picking_draft(self):
        """ test an empty still can be reset to draft """
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
        })
        self.assertFalse(picking.move_ids)
        self.assertEqual(picking.state, 'draft')
