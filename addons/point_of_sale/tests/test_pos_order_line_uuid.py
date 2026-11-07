# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon


@tagged('post_install', '-at_install')
class TestPosOrderLineUuid(TestPointOfSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uuid_product = cls.env['product.product'].create({
            'name': 'Uuid Merge Product',
            'available_in_pos': True,
            'list_price': 100.0,
            'taxes_id': [Command.clear()],
        })

    def _line(self, line_uuid, qty):
        return Command.create({
            'uuid': line_uuid,
            'product_id': self.uuid_product.id,
            'qty': qty,
            'price_unit': 100.0,
            'price_subtotal': 100.0 * qty,
            'price_subtotal_incl': 100.0 * qty,
            'discount': 0.0,
            'tax_ids': [Command.set([])],
            'pack_lot_ids': [],
        })

    def _payload(self, session, order_uuid, lines):
        return {
            'access_token': '0123456789',
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'amount_tax': 0.0,
            'amount_total': 0.0,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'last_order_preparation_change': '{}',
            'lines': lines,
            'name': 'Order 00001-001-0001',
            'partner_id': False,
            'payment_ids': [],
            'sequence_number': 1,
            'session_id': session.id,
            'state': 'draft',
            'user_id': self.env.uid,
            'uuid': order_uuid,
        }

    def test_devices_rebuilding_a_line_keep_a_single_record(self):
        """When two devices rebuild the same line, both saves must go to the record already in the database."""
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id
        order_uuid = '55555555-5555-5555-5555-555555555555'
        order_id = self.PosOrder.sync_from_ui(
            [self._payload(session, order_uuid, [self._line('rebuilt-line', 2.0)])])['pos.order'][0]['id']
        order = self.PosOrder.browse(order_id)
        line = order.lines

        # Device A rebuilds the line: it deletes the record it loaded and sends it again with the same uuid.
        self.PosOrder.sync_from_ui([self._payload(
            session, order_uuid, [Command.delete(line.id), self._line('rebuilt-line', 3.0)])])
        # Device B never saw A's save. It rebuilds the line from its own copy and adds a new one.
        self.PosOrder.sync_from_ui([self._payload(
            session, order_uuid,
            [Command.delete(line.id), self._line('rebuilt-line', 4.0), self._line('new-line', 1.0)])])

        self.assertTrue(line.exists(), "The rebuilt line must stay the same record")
        self.assertEqual(line.qty, 4.0, "The last device to save must win")
        self.assertEqual(len(order.lines), 2)
        self.assertEqual(set(order.lines.mapped('uuid')), {'rebuilt-line', 'new-line'})
