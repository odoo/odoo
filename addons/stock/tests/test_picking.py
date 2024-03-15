from odoo.tests import common
from odoo.exceptions import UserError
from odoo.tests import Form

class TestPicking(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.product = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.env['stock.quant']._update_available_quantity(cls.product, cls.stock_location, 10.0)
        cls.product_consu = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'consu',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

    def test_show_detailed(self):
        """
        Create an delivery immediate transfer with a storable and a consumable
        product. The consumable product should not create move line from quants.
        """
        # create a delivery order
        picking = Form(self.env['stock.picking'].with_context(default_picking_type_id=self.ref('stock.picking_type_out')))
        with picking.move_ids_without_package.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 1.0
        with picking.move_ids_without_package.new() as move:
            move.product_id = self.product_consu
            move.product_uom_qty = 1.0
        picking = picking.save()

        self.assertEqual(picking.move_ids[0].show_quant, True)
        self.assertEqual(picking.move_ids[1].show_quant, False)

    def test_create_move_line_reserved(self):
        """ Create a delivery immediate transfer with a storable product.
        The move line should be reserved.
        """
        # create a delivery order
        picking = Form(self.env['stock.picking'].with_context(default_picking_type_id=self.ref('stock.picking_type_out')))
        with picking.move_ids_without_package.new() as move:
            move.product_id = self.product
            move.product_uom_qty = 1.0
        picking = picking.save()
        self.env['stock.move.line'].create({
            'move_id': picking.move_ids_without_package.id,
            'product_id': self.product.id,
            'quantity': 1.0,
        })
        self.assertEqual(picking.move_ids.quantity, 1.0)
        self.assertEqual(picking.move_ids.state, 'assigned')
        self.assertEqual(picking.move_ids.picked, False)

    def test_00_no_duplicate_sequence_code(self):
        operation_type_1 = self.env['stock.picking.type'].create({
            'name':'test 1',
            'code': 'internal',
            'default_location_src_id': self.stock_location.id,
            'default_location_dest_id': self.stock_location.id,
            'sequence_code':'testpicking'
        })
        with self.assertRaises(UserError) as er:
            self.env['stock.picking.type'].create({
                'name':'test 2',
                'code': 'internal',
                'default_location_src_id': self.stock_location.id,
                'default_location_dest_id': self.stock_location.id,
                'sequence_code':'testpicking'
            })
        self.assertEqual(
            er.exception.args[0], f'Sequences {operation_type_1.sequence_id.name} already exist.')

    def test_empty_picking_draft(self):
        """ test an empty picking is set in state draft """
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
        })
        self.assertFalse(picking.move_ids)
        self.assertEqual(picking.state, 'draft')
