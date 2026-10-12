from odoo import Command
from odoo.tests import tagged

from .common import TestL10nEgEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEgEdiPosSendFlow(TestL10nEgEdiPosCommon):

    def test_send_with_invalid_data_yields_error_state_and_skips_http(self):
        """check_data failure short-circuits the send: state=error[_test],
        to_invoice=False, no http call."""
        self.eg_product_untaxed.taxes_id = [Command.set(self.eg_tax_uncoded.ids)]
        order = self._create_unpaid_order()
        with self._assert_no_eta_call():
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'error_test')
        self.assertFalse(order.to_invoice)

    def test_warning_blocking_level_keeps_state_to_send_and_clears_uuid(self):
        """A 'warning' blocking level (retryable transport error) parks the
        order in to_send with the uuid cleared for the next retry."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_response_warning()):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'to_send')
        self.assertEqual(order.l10n_eg_edi_pos_uuid, '')
        self.assertFalse(order.to_invoice)

    def test_error_blocking_level_yields_error_state_and_to_invoice_false(self):
        """A non-retryable 'error' blocking level lands the order in
        error[_test] with the uuid cleared."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_response_error()):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'error_test')
        self.assertEqual(order.l10n_eg_edi_pos_uuid, '')
        self.assertFalse(order.to_invoice)

    def test_accepted_document_yields_sent_state_with_qr_and_chatter_attachment(self):
        """Acceptance lands the order in sent[_test]: QR populated, submission
        uuid set, error cleared, envelope attached to a chatter message."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid(submission_id='SUB-A')):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'sent_test')
        self.assertTrue(order.l10n_eg_edi_pos_qr)
        self.assertEqual(order.l10n_eg_edi_pos_submission_uuid, 'SUB-A')
        self.assertEqual(order.l10n_eg_edi_pos_error, '')
        messages_with_attachment = order.message_ids.filtered(lambda m: m.attachment_ids)
        self.assertTrue(messages_with_attachment, "Expected a chatter message carrying the envelope")
        attached_envelope = messages_with_attachment.attachment_ids.filtered(
            lambda a: a.res_field == 'l10n_eg_edi_pos_json_doc_file'
        )
        self.assertTrue(attached_envelope, "Expected the envelope attachment to be linked to the chatter post")

    def test_rejected_document_yields_rejected_state_with_uuid_retained(self):
        """Rejection lands the order in rejected[_test] with the uuid retained
        so a resend can carry it as referenceOldUUID."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_rejects_any_uuid(message='Bad VAT')):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'rejected_test')
        self.assertTrue(order.l10n_eg_edi_pos_uuid)
        self.assertIn('Bad VAT', order.l10n_eg_edi_pos_error)
        self.assertFalse(order.to_invoice)

    def test_unknown_response_shape_yields_error_state(self):
        """Empty data with no accept/reject for the uuid falls through to the
        "Unexpected response from ETA." error branch."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_response_unknown()):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'error_test')
        self.assertIn('Unexpected response from ETA', order.l10n_eg_edi_pos_error)
        self.assertEqual(order.l10n_eg_edi_pos_uuid, '')

    def test_first_accepted_receipt_seeds_chain(self):
        """The first accepted receipt populates config.l10n_eg_edi_pos_last_uuid;
        that value becomes the previousUUID of the next receipt."""
        self.assertFalse(self.eg_pos_config.sudo().l10n_eg_edi_pos_last_uuid)
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(order)
        self.assertEqual(self.eg_pos_config.sudo().l10n_eg_edi_pos_last_uuid, order.l10n_eg_edi_pos_uuid)

    def test_rejected_receipt_does_not_advance_chain(self):
        """A rejected receipt does not update config.last_uuid — the chain
        head stays at the previous accepted receipt's uuid."""
        first = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(first)
        chain_head = self.eg_pos_config.sudo().l10n_eg_edi_pos_last_uuid

        second = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_rejects_any_uuid(message='Nope')):
            self._pay(second)
        self.assertEqual(self.eg_pos_config.sudo().l10n_eg_edi_pos_last_uuid, chain_head)

    def test_errored_receipt_does_not_advance_chain(self):
        """A transport-errored receipt does not update config.last_uuid."""
        first = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(first)
        chain_head = self.eg_pos_config.sudo().l10n_eg_edi_pos_last_uuid

        second = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_response_error()):
            self._pay(second)
        self.assertEqual(self.eg_pos_config.sudo().l10n_eg_edi_pos_last_uuid, chain_head)

    def test_accepted_refund_advances_chain(self):
        """An accepted refund advances config.last_uuid to the refund's uuid."""
        original = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(original)
        refund = self._refund_of(original)
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(refund)
        self.assertEqual(self.eg_pos_config.sudo().l10n_eg_edi_pos_last_uuid, refund.l10n_eg_edi_pos_uuid)
