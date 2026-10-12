from odoo.tests import tagged

from .common import TestL10nEgEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEgEdiPosEnvelope(TestL10nEgEdiPosCommon):

    def test_envelope_written_on_errored_send(self):
        """A transport-errored send still populates ``l10n_eg_edi_pos_json_doc_file``
        with the request and the error response (audit requirement)."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_response_error()):
            self._pay(order)
        self.assertEqual(order.l10n_eg_edi_pos_state, 'error_test')
        self.assertTrue(order.l10n_eg_edi_pos_json_doc_file)

        envelope = self._read_envelope_json(order)
        self.assertIn('request', envelope)
        self.assertIn('response', envelope)

    def test_resend_overwrites_envelope_and_invalidates_cache(self):
        """A resend overwrites the envelope with the new request/response and
        invalidates the recordset cache so reads return the fresh bytes."""
        order = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_response_error(message='first try')):
            self._pay(order)
        envelope_first = self._read_envelope_json(order)

        with self._mock_eta(send_response=self._eta_accepts_any_uuid(submission_id='SUB-RESENT')):
            order.action_l10n_eg_edi_pos_resend()
        envelope_second = self._read_envelope_json(order)

        self.assertNotEqual(envelope_first, envelope_second)
        self.assertEqual(envelope_second['response'].get('submissionId'), 'SUB-RESENT')

    def test_chatter_attachment_only_linked_on_accept(self):
        """A chatter message carrying the envelope attachment is posted only on
        accept; reject/error leave the envelope unattached to chatter."""
        accepted = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_accepts_any_uuid()):
            self._pay(accepted)
        accepted_envelope_messages = accepted.message_ids.filtered(
            lambda m: any(a.res_field == 'l10n_eg_edi_pos_json_doc_file' for a in m.attachment_ids)
        )
        self.assertTrue(accepted_envelope_messages, "Expected a chatter message linking the envelope on accept")

        rejected = self._create_unpaid_order()
        with self._mock_eta(send_response=self._eta_rejects_any_uuid()):
            self._pay(rejected)
        self.assertTrue(rejected.l10n_eg_edi_pos_json_doc_file, "Envelope must still be written on reject")
        rejected_envelope_messages = rejected.message_ids.filtered(
            lambda m: any(a.res_field == 'l10n_eg_edi_pos_json_doc_file' for a in m.attachment_ids)
        )
        self.assertFalse(rejected_envelope_messages, "Reject must not link the envelope to a chatter message")
