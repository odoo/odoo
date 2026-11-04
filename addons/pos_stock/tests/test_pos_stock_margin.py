import odoo
from odoo.addons.pos_stock.tests.common import CommonPosStockTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPosStockMargin(CommonPosStockTest):
    """
    Test the margin computation on orders with basic configuration
    The tests contain the base scenarios.
    """
    _test_user_groups = None  # FIXME list needed groups

    def setUp(self):
        super().setUp()
        self.config = self.pos_config_usd
        self.categ_basic = self.env.ref('product.product_category_services')
        self.categ_anglo = self.stock_account_product_categ
        self.env.company.anglo_saxon_accounting = True
        self.env.company.point_of_sale_update_stock_quantities = 'real'

        self.stock_location = self.env['stock.warehouse'].sudo().create({
            'partner_id': self.env.user.partner_id.id,
            'name': 'Stock location',
            'code': 'WH'
        }).lot_stock_id
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')

    def test_fifo_margin_real_time(self):
        """
        Test margin where there is product in FIFO with stock update in real time
        """

        product1 = self.create_product('Product 1', 10, standard_price=5, categ_id=self.categ_anglo.id)
        product2 = self.create_product('Product 2', 50, standard_price=30, categ_id=self.categ_basic.id)

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product1.id,
            'uom_id': self.uom_unit.id,
            'product_uom_qty': 2,
            'price_unit': 3,
            'value_manual': 6,
        }).sudo()
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 2
        move1.picked = True
        move1._action_done()

        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product1.id,
            'uom_id': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 7,
            'value_manual': 7,
        }).sudo()
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 1
        move2.picked = True
        move2._action_done()

        # open a session
        self.open_new_session()

        # create orders
        self.create_orders([
            {'lines': [(product1, 1), (product2, 1)]},
            {'lines': [(product1, 2)]},
        ])

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 27)
        self.assertEqual(self.pos_session.order_ids[1].margin, 10)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.45)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.5)

        # close session
        self.close_pos_session()

    def test_avco_margin_closing_time(self):
        """
        Test margin where there is product in AVCO with stock update in closing
        """

        self.categ_anglo.property_cost_method = 'average'
        product1 = self.create_product('Product 1', 10, standard_price=5, categ_id=self.categ_anglo.id)
        product2 = self.create_product('Product 2', 50, standard_price=30, categ_id=self.categ_basic.id)
        self.env.company.point_of_sale_update_stock_quantities = 'closing'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product1.id,
            'uom_id': self.uom_unit.id,
            'product_uom_qty': 2,
            'price_unit': 3,
            'value_manual': 6,
        }).sudo()
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 2
        move1.picked = True
        move1._action_done()

        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product1.id,
            'uom_id': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 6,
            'value_manual': 6,
        }).sudo()
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 1
        move2.picked = True
        move2._action_done()

        # open a session
        self.open_new_session()

        # create orders
        self.create_orders([
            {'lines': [(product1, 1), (product2, 1)]},
            {'lines': [(product1, 2)]},
        ])

        # check margins which are not really computed so it should be 0
        self.assertEqual(self.pos_session.order_ids[0].margin, 0)
        self.assertEqual(self.pos_session.order_ids[1].margin, 0)

        # check margins percent (same as above)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0)

        # close session
        self.close_pos_session()

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 26)
        self.assertEqual(self.pos_session.order_ids[1].margin, 12)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.4333)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.6)

        self.env.company.point_of_sale_update_stock_quantities = 'real'
