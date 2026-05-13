from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestL10nEgEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEgEdiPosActionPaid(TestL10nEgEdiPosCommon):

    def test_replay_on_already_sent_order_is_idempotent(self):
        """Replaying ``action_pos_order_paid`` on an order in sent[_test] does
        not re-send (the http layer is not called)."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'sent_test')

        with self._assert_no_eta_call():
            order.action_pos_order_paid()

    def test_business_buyer_raises_user_error_before_super(self):
        """Selling to an EG business buyer (is_company=True) raises UserError
        before super() — no state change, no ETA call."""
        order = self._create_unpaid_order(partner=self.eg_business_customer)
        with self._assert_no_eta_call(), self.assertRaises(UserError):
            self._pay(order)

    def test_refund_with_business_buyer_does_not_raise(self):
        """Refund path is exempt from the business-buyer guard — the action
        proceeds even when the partner is_company=True."""
        original = self._create_unpaid_order(partner=self.eg_individual_customer)
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(original)
        original.partner_id = self.eg_business_customer
        refund = self._refund_of(original)
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(refund)
        self.assertEqual(refund.l10n_eg_edi_pos_state, 'sent_test')

    def test_resend_after_rejected_carries_reference_old_uuid(self):
        """A resend of a rejected[_test] order rebuilds the payload with
        header.referenceOldUUID set to the retained uuid."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_rejects_any_uuid()):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'rejected_test')
        rejected_uuid = order.l10n_eg_edi_pos_uuid
        self.assertTrue(rejected_uuid)

        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            order.action_l10n_eg_edi_pos_resend()
        header = self._read_envelope_json(order)['request']['header']
        self.assertEqual(header.get('referenceOldUUID'), rejected_uuid)

    def test_resend_after_error_has_no_reference_old_uuid(self):
        """A resend of an error[_test] order (uuid cleared) rebuilds the
        payload without header.referenceOldUUID."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_response_error()):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'error_test')
        self.assertFalse(order.l10n_eg_edi_pos_uuid)

        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            order.action_l10n_eg_edi_pos_resend()
        header = self._read_envelope_json(order)['request']['header']
        self.assertNotIn('referenceOldUUID', header)
