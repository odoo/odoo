# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.purchase_peppol.models.purchase_order import Event


@tagged('post_install', '-at_install')
class TestPeppolPurchaseOrderFlow(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.vat = 'NL123456782B90'
        cls.env.company.vat = 'BE0477472701'
        cls.po = cls.env['purchase.order'].create({
            'name': 'Test PO',
            'partner_id': cls.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': cls.product_a.id,
                'name': 'Product A',
                'product_qty': 10.0,
                'price_unit': 50.0,
            })],
        })

    def test_send_initial_order(self):
        """Test sending initial order: Draft -> Pending, tracker created."""
        po = self.po
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'draft')
        self.assertEqual(len(po.edi_tracker_ids), 0)

        po.action_send_advanced_order()
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'pending_response')
        self.assertEqual(len(po.edi_tracker_ids), 1)

        tracker = po.edi_tracker_ids[0]
        self.assertEqual(tracker.state, 'sent')
        self.assertEqual(tracker.document_type, 'order')
        self.assertEqual(tracker.sequence, 0)

    def test_receive_order_accept(self):
        """Test receiving order accept: Pending -> Confirmed, tracker accepted, order confirmed."""
        po = self.po
        po.action_send_advanced_order()
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'pending_response')

        po.process_event(Event.RECEIVE_AP)
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'confirmed')
        self.assertEqual(po.state, 'purchase')

        tracker = po.edi_tracker_ids[0]
        self.assertEqual(tracker.state, 'accepted')

        messages = po.message_ids.filtered(lambda m: 'Order is accepted by the seller' in m.body)
        self.assertTrue(messages)

    def test_receive_order_reject(self):
        """Test receiving order reject: Pending -> Cancelled, order cancelled."""
        po = self.po
        po.action_send_advanced_order()
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'pending_response')

        po.process_event(Event.RECEIVE_RE)
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'cancelled')
        self.assertEqual(po.state, 'cancel')

        messages = po.message_ids.filtered(lambda m: 'Order is rejected by the seller' in m.body)
        self.assertTrue(messages)

    def test_send_order_change(self):
        """Test sending order change: Confirmed -> Change Pending, new tracker."""
        po = self.po
        po.action_send_advanced_order()
        po.process_event(Event.RECEIVE_AP)
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'confirmed')

        initial_tracker_count = len(po.edi_tracker_ids)
        po.action_send_order_change()
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'change_pending')
        self.assertEqual(len(po.edi_tracker_ids), initial_tracker_count + 1)

        new_tracker = po.edi_tracker_ids.filtered(lambda t: t.document_type == 'order_change')[0]
        self.assertEqual(new_tracker.state, 'sent')
        self.assertEqual(new_tracker.sequence, 1)

    def test_receive_change_accept(self):
        """Test receiving change accept: Change Pending -> Confirmed."""
        po = self.po
        po.action_send_advanced_order()
        po.process_event(Event.RECEIVE_AP)
        po.action_send_order_change()
        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'change_pending')

        po.process_event(Event.RECEIVE_AP)

        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'confirmed')
        messages = po.message_ids.filtered(lambda m: 'Order change request is accepted by the seller' in m.body)
        self.assertTrue(messages)

    def test_receive_change_reject(self):
        """Test receiving change reject: Change Pending -> Confirmed, revert order."""
        po = self.po
        po.action_send_advanced_order()
        po.process_event(Event.RECEIVE_AP)
        po.action_send_order_change()
        po.process_event(Event.RECEIVE_RE)

        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'confirmed')
        messages = po.message_ids.filtered(lambda m: 'Order change request is rejected by the seller' in m.body)
        self.assertTrue(messages)

    def test_send_order_cancel(self):
        """Test sending order cancel: Confirmed -> Cancel Pending, new tracker."""
        po = self.po
        po.action_send_advanced_order()
        po.process_event(Event.RECEIVE_AP)
        initial_tracker_count = len(po.edi_tracker_ids)

        po.action_send_order_cancel()

        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'cancellation_pending')
        self.assertEqual(len(po.edi_tracker_ids), initial_tracker_count + 1)
        new_tracker = po.edi_tracker_ids.filtered(lambda t: t.document_type == 'order_cancel')[0]
        self.assertEqual(new_tracker.state, 'sent')

    def test_receive_cancel_accept(self):
        """Test receiving cancel accept: Cancel Pending -> Cancelled."""
        po = self.po
        po.action_send_advanced_order()
        po.process_event(Event.RECEIVE_AP)
        po.action_send_order_cancel()
        po.process_event(Event.RECEIVE_RE)

        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'cancelled')
        self.assertEqual(po.state, 'cancel')
        messages = po.message_ids.filtered(lambda m: 'Order cancellation request is accepted by the seller' in m.body)
        self.assertTrue(messages)

    def test_receive_cancel_reject(self):
        """Test receiving cancel reject: Cancel Pending -> Confirmed."""
        po = self.po
        po.action_send_advanced_order()
        po.process_event(Event.RECEIVE_AP)
        po.action_send_order_cancel()
        po.process_event(Event.RECEIVE_AP)

        self.assertEqual(po.l10n_sg_peppol_advanced_order_state, 'confirmed')
        self.assertEqual(po.state, 'purchase')
        messages = po.message_ids.filtered(lambda m: 'Order cancellation request is rejected by the seller' in m.body)
        self.assertTrue(messages)

    def test_invalid_event(self):
        """Test invalid event raises ValidationError."""
        po = self.po
        # Try to send change from draft
        with self.assertRaises(ValidationError):
            po.process_event(Event.RECEIVE_AP)  # No transition for draft + RECEIVE_AP

    def test_edi_tracker_computation(self):
        """Test edi_tracker_ids computation."""
        po = self.po
        po.action_send_advanced_order()
        self.assertEqual(len(po.edi_tracker_ids), 1)
        # Add more trackers if needed, but for now, basic check
