import contextlib
import logging
from unittest.mock import patch

import odoo
from odoo.addons.point_of_sale.models.pos_order import PosOrder
from odoo.addons.point_of_sale.models.pos_session import PosSession
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


class IntendedException(Exception):
    pass


def mocked_process_order(*args):
    # We just want the order process to crash (to see if it is captured)
    raise IntendedException()


def mocked_handle_order_process_fail(self, order: dict, exception: Exception, draft: bool):
    # We DO NOT want to create a new env in the test as the current pos_session does not exist (as it was not committed)
    self._process_order_process_fail(order, exception)


@odoo.tests.tagged('post_install', '-at_install')
class TestPosCapture(TestPoSCommon):
    """
    Test the capture system of failed to process orders
    """

    def setUp(self):
        super().setUp()
        self.config = self.basic_config

        self.product1 = self.create_product('Product 1', self.categ_basic, 10, 5)

    def assert_activity_and_attachment(self, pos_session, number):
        pos_attachments_domain = [
            ['res_model', '=', pos_session._name],
            ['res_id', '=', pos_session.id]
        ]
        self.assertEqual(len(pos_session.activity_ids), number)
        self.assertEqual(len(self.env['ir.attachment'].search(pos_attachments_domain)), number)

    def test_capture_one_order(self):
        # open a session
        session = self.open_new_session()

        orders = [self.create_ui_order_data([(self.product1, 1)])]

        self.assert_activity_and_attachment(session, 0)
        with patch.object(PosOrder, '_process_order', mocked_process_order),\
             patch.object(PosSession, '_handle_order_process_fail', mocked_handle_order_process_fail),\
             self.assertLogs('odoo.addons.point_of_sale.models.pos_order', level=logging.ERROR) as logger_error_output:
            try:
                self.env['pos.order'].create_from_ui(orders)
            except IntendedException:
                self.assertIn("An error occurred when processing the PoS order", logger_error_output.output[0])
                self.assert_activity_and_attachment(session, 1)
                self.assertEqual(session.activity_ids[0].user_id.id, self.env.user.id)

    def test_capture_two_orders(self):
        """Two order even with same content should have distinct captured file"""
        # open a session
        session = self.open_new_session()

        order1 = [self.create_ui_order_data([(self.product1, 1)], uid='12345-678-1996')]
        order2 = [self.create_ui_order_data([(self.product1, 1)], uid='12345-678-1999')]  # Different order with same content but different uuid

        with patch.object(PosOrder, '_process_order', mocked_process_order),\
             patch.object(PosSession, '_handle_order_process_fail', mocked_handle_order_process_fail),\
             self.assertLogs('odoo.addons.point_of_sale.models.pos_order', level=logging.ERROR):
            try:
                self.env['pos.order'].create_from_ui(order1)
            except IntendedException:
                self.assert_activity_and_attachment(session, 1)

            try:
                self.env['pos.order'].create_from_ui(order2)
            except IntendedException:
                self.assert_activity_and_attachment(session, 2)

    def test_capture_one_order_twice(self):
        """Should have only one attachment as we sync the same order twice"""
        # open a session
        session = self.open_new_session()

        orders = [self.create_ui_order_data([(self.product1, 1)])]

        self.assert_activity_and_attachment(session, 0)
        with patch.object(PosOrder, '_process_order', mocked_process_order),\
             patch.object(PosSession, '_handle_order_process_fail', mocked_handle_order_process_fail),\
             self.assertLogs('odoo.addons.point_of_sale.models.pos_order', level=logging.ERROR):
            for _ in range(2):
                try:
                    self.env['pos.order'].create_from_ui(orders)
                except IntendedException:
                    self.assert_activity_and_attachment(session, 1)

    def test_capture_order_same_uuid(self):
        """Should have 2 attachments as the content is different"""
        # open a session
        session = self.open_new_session()

        order1 = [self.create_ui_order_data([(self.product1, 1)], uid='12345-678-1996')]
        order2 = [self.create_ui_order_data([(self.product1, 2)], uid='12345-678-1996')]

        self.assert_activity_and_attachment(session, 0)
        with patch.object(PosOrder, '_process_order', mocked_process_order),\
             patch.object(PosSession, '_handle_order_process_fail', mocked_handle_order_process_fail),\
             self.assertLogs('odoo.addons.point_of_sale.models.pos_order', level=logging.ERROR):
            try:
                self.env['pos.order'].create_from_ui(order1)
            except IntendedException:
                self.assert_activity_and_attachment(session, 1)

            try:
                self.env['pos.order'].create_from_ui(order2)
            except IntendedException:
                self.assert_activity_and_attachment(session, 2)

    def test_capture_one_order_and_removed(self):
        """Check if the attachment and activity is automatically remove after the order sync"""
        # open a session
        session = self.open_new_session()

        orders = [self.create_ui_order_data([(self.product1, 1)])]

        self.assert_activity_and_attachment(session, 0)
        with patch.object(PosOrder, '_process_order', mocked_process_order),\
             patch.object(PosSession, '_handle_order_process_fail', mocked_handle_order_process_fail),\
             self.assertLogs('odoo.addons.point_of_sale.models.pos_order', level=logging.ERROR),\
             contextlib.suppress(IntendedException):
            self.env['pos.order'].create_from_ui(orders)

        self.assert_activity_and_attachment(session, 1)
        # Resync the order, this time it should go through!
        self.env['pos.order'].create_from_ui(orders)
        # Should automatically remove the attachment for this order after sync
        self.assert_activity_and_attachment(session, 0)

    def test_capture_two_orders_and_removed(self):
        """Check if the attachment and activity is automatically remove after the order sync (with 2 orders)"""
        # open a session
        session = self.open_new_session()

        order1 = [self.create_ui_order_data([(self.product1, 1)], uid='12345-678-1996')]
        order2 = [self.create_ui_order_data([(self.product1, 1)], uid='12345-678-1999')]  # Different order with same content but different uuid

        with patch.object(PosOrder, '_process_order', mocked_process_order),\
             patch.object(PosSession, '_handle_order_process_fail', mocked_handle_order_process_fail),\
             self.assertLogs('odoo.addons.point_of_sale.models.pos_order', level=logging.ERROR):
            try:
                self.env['pos.order'].create_from_ui(order1)
            except IntendedException:
                self.assert_activity_and_attachment(session, 1)

            try:
                self.env['pos.order'].create_from_ui(order2)
            except IntendedException:
                self.assert_activity_and_attachment(session, 2)

        self.assert_activity_and_attachment(session, 2)
        # Resync the order, this time it should go through!
        self.env['pos.order'].create_from_ui(order2)
        # Should automatically remove the attachment for this order after sync
        self.assert_activity_and_attachment(session, 1)

        self.env['pos.order'].create_from_ui(order1)
        # Should automatically remove the attachment for this order after sync
        self.assert_activity_and_attachment(session, 0)
