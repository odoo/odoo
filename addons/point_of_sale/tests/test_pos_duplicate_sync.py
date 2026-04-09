# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosDuplicateSync(TestPoSCommon):

    def test_duplicate_sync(self):
        """Syncing the same draft order twice must not raise a UniqueViolation on line/payment UUIDs."""
        self.config = self.basic_config
        self.open_new_session()
        product = self.create_product('Test Product', self.categ_basic, 10.0)

        order_uuid = 'test-order-uuid-unique-1'
        line_uuid = 'test-line-uuid-unique-1'
        order_data = self.create_ui_order_data([(product, 1)], uuid=order_uuid)
        order_data['lines'][0][2]['uuid'] = line_uuid
        # Keep the order in draft so the second sync actually re-processes lines.
        order_data['payment_ids'] = []
        order_data['amount_paid'] = 0

        # First sync: creates the order.
        self.env['pos.order'].sync_from_ui([order_data])
        order = self.env['pos.order'].search([('uuid', '=', order_uuid)])
        self.assertTrue(order)
        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines.uuid, line_uuid)

        # Second sync with identical data: must update, not duplicate.
        self.env['pos.order'].sync_from_ui([order_data])
        self.assertEqual(len(order.lines), 1)
