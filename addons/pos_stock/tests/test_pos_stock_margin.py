from unittest import skip

import odoo
from odoo.addons.point_of_sale.tests.test_pos_margin import TestPosMargin


@odoo.tests.tagged('post_install', '-at_install')
class TestPosStockMargin(TestPosMargin):
    """
    Test the margin computation on orders with basic configuration
    The tests contain the base scenarios.
    """

    def setUp(self):
        super().setUp()
        self.config = self.basic_config

        self.stock_location = self.env['stock.warehouse'].create({
            'partner_id': self.env.user.partner_id.id,
            'name': 'Stock location',
            'code': 'WH'
        }).lot_stock_id
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')

    @skip('Temporary to fast merge new valuation')
    def test_fifo_margin_real_time(self):
        """
        Test margin where there is product in FIFO with stock update in real time
        """

        product1 = self.create_product('Product 1', self.categ_anglo, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'price_unit': 3,
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
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 7,
        }).sudo()
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 1
        move2.picked = True
        move2._action_done()

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1), (product2, 1)]),
                  self.create_ui_order_data([(product1, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 27)
        self.assertEqual(self.pos_session.order_ids[1].margin, 10)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.45)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.5)

        # close session
        self.pos_session.action_pos_session_validate()

    @skip('Temporary to fast merge new valuation')
    def test_avco_margin_closing_time(self):
        """
        Test margin where there is product in AVCO with stock update in closing
        """

        self.categ_anglo.property_cost_method = 'average'
        product1 = self.create_product('Product 1', self.categ_anglo, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)
        self.env.company.point_of_sale_update_stock_quantities = 'closing'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'price_unit': 3,
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
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 6,
        }).sudo()
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 1
        move2.picked = True
        move2._action_done()

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1), (product2, 1)]),
                  self.create_ui_order_data([(product1, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins which are not really computed so it should be 0
        self.assertEqual(self.pos_session.order_ids[0].margin, 0)
        self.assertEqual(self.pos_session.order_ids[1].margin, 0)

        # check margins percent (same as above)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0)

        # close session
        total_cash_payment = sum(self.pos_session.mapped('order_ids.payment_ids').filtered(lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        self.pos_session.post_closing_cash_details(total_cash_payment)
        self.pos_session.close_session_from_ui()

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 26)
        self.assertEqual(self.pos_session.order_ids[1].margin, 12)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.4333)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.6)

        self.env.company.point_of_sale_update_stock_quantities = 'real'
