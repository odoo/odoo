# -*- coding: utf-8 -*-

import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPosMargin(TestPoSCommon):
    """
    Test the margin computation on orders with basic configuration
    The tests contain the base scenarios.
    """

    def setUp(self):
        super(TestPosMargin, self).setUp()
        self.config = self.basic_config

        self.stock_location = self.env['stock.warehouse'].create({
            'partner_id': self.env.user.partner_id.id,
            'name': 'Stock location',
            'code': 'WH'
        }).lot_stock_id
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')


    def test_positive_margin(self):
        """
        Test margin where it should be more than zero
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 5)
        self.assertEqual(self.pos_session.order_ids[1].margin, 20)
        self.assertEqual(self.pos_session.order_ids[2].margin, 50)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), 0.42)

        # close session
        self.pos_session.action_pos_session_validate()

    def test_negative_margin(self):
        """
        Test margin where it should be less than zero
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 15)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 100)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, -5)
        self.assertEqual(self.pos_session.order_ids[1].margin, -50)
        self.assertEqual(self.pos_session.order_ids[2].margin, -110)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, -0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, -1)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), -0.92)

        # close session
        self.pos_session.action_pos_session_validate()

    def test_full_margin(self):
        """
        Test margin where the product cost is always 0
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10)
        product2 = self.create_product('Product 2', self.categ_basic, 50)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 10)
        self.assertEqual(self.pos_session.order_ids[1].margin, 50)
        self.assertEqual(self.pos_session.order_ids[2].margin, 120)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 1)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 1)
        self.assertEqual(self.pos_session.order_ids[2].margin_percent, 1)

        # close session
        self.pos_session.action_pos_session_validate()

    def test_tax_margin(self):
        """
        Test margin with tax on products
        Product 1 price without tax = 10
        Product 2 price without tax = 50
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5, self.taxes['tax7'].ids)
        product2 = self.create_product('Product 2', self.categ_basic, 55, 30, self.taxes['tax10'].ids)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 5)
        self.assertEqual(self.pos_session.order_ids[1].margin, 20)
        self.assertEqual(self.pos_session.order_ids[2].margin, 50)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), 0.42)

        # close session
        self.pos_session.action_pos_session_validate()

    def test_other_currency_margin(self):
        """
        Test margin with tax on products and with different currency
        The currency rate is 0.5 so the product price is halved in this currency.
        """

        # change the config
        current_config = self.config
        self.config = self.other_currency_config

        # same parameters as test_positive_margin
        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins in the config currency
        self.assertEqual(self.pos_session.order_ids[0].margin, 2.5)
        self.assertEqual(self.pos_session.order_ids[1].margin, 10)
        self.assertEqual(self.pos_session.order_ids[2].margin, 25)

        # check margins percent which should be the same as test_positive_margin
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), 0.42)

        # close session
        self.pos_session.action_pos_session_validate()

        # set the config back
        self.config = current_config

    def test_tax_and_other_currency_margin(self):
        """
        Test margin with different currency between products and config with taxes.
        Product 1 price without tax = 10
        Product 2 price without tax = 50
        The currency rate is 0.5 so the product price is halved in this currency.
        """

        # change the config
        current_config = self.config
        self.config = self.other_currency_config

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5, self.taxes['tax7'].ids)
        product2 = self.create_product('Product 2', self.categ_basic, 55, 30, self.taxes['tax10'].ids)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins in the config currency
        self.assertEqual(self.pos_session.order_ids[0].margin, 2.5)
        self.assertEqual(self.pos_session.order_ids[1].margin, 10)
        self.assertEqual(self.pos_session.order_ids[2].margin, 25)

        # check margins percent which should be the same as test_tax_margin
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(self.pos_session.order_ids[2].margin_percent, 0.4167)

        # close session
        self.pos_session.action_pos_session_validate()

        # set the config back
        self.config = current_config

    def test_return_margin(self):
        """
        Test margin where we return product (negative line quantity)
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, -1)]),
                  self.create_ui_order_data([(product2, -1)]),
                  self.create_ui_order_data([(product1, -2), (product2, -2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, -5)
        self.assertEqual(self.pos_session.order_ids[1].margin, -20)
        self.assertEqual(self.pos_session.order_ids[2].margin, -50)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), 0.42)

        # close session
        self.pos_session.action_pos_session_validate()

    def test_fifo_margin_real_time(self):
        """
        Test margin where there is product in FIFO with stock update in real time
        """

        product1 = self.create_product('Product 1', self.categ_anglo, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        move1 = self.env['stock.move'].create({
            'name': 'IN 2 unit @ 3 per unit',
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
            'name': 'IN 1 unit @ 7 per unit',
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

    def test_avco_margin_closing_time(self):
        """
        Test margin where there is product in AVCO with stock update in closing
        """

        self.categ_anglo.property_cost_method = 'average'
        product1 = self.create_product('Product 1', self.categ_anglo, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)
        self.env.company.point_of_sale_update_stock_quantities = 'closing'


        move1 = self.env['stock.move'].create({
            'name': 'IN 2 unit @ 3 per unit',
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
            'name': 'IN 1 unit @ 6 per unit',
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
