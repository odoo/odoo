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
