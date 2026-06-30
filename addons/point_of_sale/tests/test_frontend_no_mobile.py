# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestFrontendNoMobile(TestPointOfSaleHttpCommon):
    def test_editing_payment_no_duplicate(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_editing_payment_no_duplicate')
        orders = self.main_pos_config.current_session_id.order_ids  # Two orders created in the tour

        # Create an order with a payment of 50, then edit it to 100 and validate.
        # Amount return should be 96.8, do not edit the change line during payment editing
        first_order = orders[1]
        self.assertEqual(len(first_order.payment_ids), 2)
        self.assertEqual(first_order.payment_ids[0].amount, -96.8)
        self.assertEqual(first_order.payment_ids[1].amount, 100)
        self.assertEqual(first_order.amount_paid, 3.2)
        self.assertEqual(first_order.amount_total, 3.2)
        self.assertEqual(first_order.amount_return, 96.8)

        # Create a new order with a payment of 100, then edit it to 50 and validate.
        # Amount return should be 46.8, delete the change line during payment editing
        second_order = orders[0]
        self.assertEqual(len(second_order.payment_ids), 2)
        self.assertEqual(second_order.payment_ids[0].amount, -46.8)
        self.assertEqual(second_order.payment_ids[1].amount, 50)
        self.assertEqual(second_order.amount_paid, 3.2)
        self.assertEqual(second_order.amount_total, 3.2)
        self.assertEqual(second_order.amount_return, 46.8)
