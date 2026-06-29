import base64
from unittest.mock import patch

from odoo.addons.l10n_ro_edi.tests.common import TestROEdiCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "-at_install", "post_install")
class TestRoEdi(TestROEdiCommon):
    _test_groups = None  # FIXME list needed groups

    def test_documents_only_deleted_on_validation(self):
        """Test that historical refused documents are preserved on resend and only cleaned up on validation.

        Flow:
        1. Send invoice → invoice_sent doc created
        2. Fetch → SPV refuses → invoice_sent deleted, invoice_refused created (1 doc)
        3. Resend succeeds → old invoice_refused preserved, invoice_sent created (2 docs)
        4. Fetch → SPV validates → all previous docs deleted, only invoice_validated remains (1 doc)
        """
        invoice = self.create_invoice()

        # Step 1: First send succeeds, index 'AA' received
        self.send_invoice_with_mock(invoice, {"key_loading": "AA"})
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_sent")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

        # Step 2: SPV refuses via fetch → sent doc deleted, refused doc created
        with patch(
            'odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_fetch_status',
            return_value={"key_download": "DL_AA", "state_status": "nok"},
        ), patch(
            'odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_download_answer',
            return_value={
                "signature": {
                    "attachment_raw": b"<xml>sig_aa</xml>",
                    "key_signature": "KEY_SIG_AA",
                    "key_certificate": "KEY_CERT_AA",
                },
                "invoice": {"error": "XML validation failed by SPV"},
            },
        ):
            invoice._l10n_ro_edi_fetch_invoice_sent_documents()

        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_refused")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)
        self.assertEqual(invoice.l10n_ro_edi_document_ids.state, "invoice_refused")

        # Step 3: Resend succeeds → refused doc preserved, new sent doc added
        invoice.button_draft()
        invoice.action_post()
        self.send_invoice_with_mock(invoice, {"key_loading": "BB"})

        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_sent")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 2)
        refused_docs = invoice.l10n_ro_edi_document_ids.filtered(lambda d: d.state == "invoice_refused")
        sent_docs = invoice.l10n_ro_edi_document_ids.filtered(lambda d: d.state == "invoice_sent")
        self.assertEqual(len(refused_docs), 1)
        self.assertEqual(len(sent_docs), 1)

        # Step 4: SPV validates → all old docs deleted, only invoice_validated remains
        with patch(
            'odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_fetch_status',
            return_value={"key_download": "DL_BB", "state_status": "ok"},
        ), patch(
            'odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_download_answer',
            return_value={
                "signature": {
                    "attachment_raw": b"<xml>sig_bb</xml>",
                    "key_signature": "KEY_SIG_BB",
                    "key_certificate": "KEY_CERT_BB",
                },
                "invoice": {"name": invoice.name},
            },
        ):
            invoice._l10n_ro_edi_fetch_invoice_sent_documents()

        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_validated")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)
        self.assertEqual(invoice.l10n_ro_edi_document_ids.state, "invoice_validated")

    def test_resend_after_refusal_synchronize_skips_old_refusal(self):
        """Test that when an invoice is refused and resent without receiving an index (server timeout),
        the subsequent synchronize correctly validates it via name matching and skips the old refusal message.

        Flow:
        1. Send invoice → invoice_sent, index='AA'
        2. Fetch → SPV refuses (nok) → invoice_refused, index persists as 'AA'
        3. Reset to draft, repost, resend → timeout (no index) → invoice_not_indexed, index=False
        4. Synchronize returns: BB accepted (matched by name) + AA refused (skipped: index=False, state≠invoice_sent)
        5. Expected: invoice_validated with index='BB', all old docs cleaned up
        """
        invoice = self.create_invoice()

        # Step 1: First send succeeds, index 'AA' received
        self.send_invoice_with_mock(invoice, {"key_loading": "AA"})
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_sent")
        self.assertEqual(invoice.l10n_ro_edi_index, "AA")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)

        # Step 2: SPV refuses via fetch (status 'nok') → invoice_sent deleted, invoice_refused created
        with patch(
            'odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_fetch_status',
            return_value={"key_download": "DL_AA", "state_status": "nok"},
        ), patch(
            'odoo.addons.l10n_ro_edi.models.account_move._request_ciusro_download_answer',
            return_value={
                "signature": {
                    "attachment_raw": b"<xml>sig_aa</xml>",
                    "key_signature": "KEY_SIG_AA",
                    "key_certificate": "KEY_CERT_AA",
                },
                "invoice": {"error": "XML validation failed by SPV"},
            },
        ):
            invoice._l10n_ro_edi_fetch_invoice_sent_documents()

        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_refused")
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)
        self.assertEqual(invoice.l10n_ro_edi_document_ids.state, "invoice_refused")
        self.assertEqual(invoice.l10n_ro_edi_index, "AA")  # index persists after refusal

        # Step 3: Reset to draft and resend; timeout means no index is received from SPV
        invoice.button_draft()
        invoice.action_post()
        self.send_invoice_with_mock(invoice, {"key_loading": False})

        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_not_indexed")
        self.assertEqual(invoice.l10n_ro_edi_index, False)
        # Historical refused doc is preserved alongside the new sent doc (traceability)
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 2)
        self.assertTrue(any(d.state == "invoice_refused" for d in invoice.l10n_ro_edi_document_ids))
        self.assertTrue(any(d.state == "invoice_sent" for d in invoice.l10n_ro_edi_document_ids))

        # Step 4: Synchronize returns both messages: old refusal 'AA' + new acceptance 'BB'
        # 'BB' is matched by invoice name since l10n_ro_edi_index is False and state is invoice_not_indexed
        # 'AA' is skipped: domain requires l10n_ro_edi_index='AA' and l10n_ro_edi_state='invoice_sent', neither matches
        invoice_name = invoice.name
        self.synchronize_with_mock({
            "sent_invoices_accepted_messages": [
                {
                    "id_solicitare": "BB",
                    "id": "MSG_BB",
                    "answer": {
                        "signature": {
                            "attachment_raw": base64.b64encode(b"<xml>signature_bb</xml>"),
                            "key_signature": "KEY_SIG_BB",
                            "key_certificate": "KEY_CERT_BB",
                        },
                        "invoice": {"name": invoice_name},
                    },
                },
            ],
            "sent_invoices_refused_messages": [
                {
                    "id_solicitare": "AA",
                    "id": "MSG_AA",
                    "answer": {
                        "signature": {
                            "attachment_raw": base64.b64encode(b"<xml>sig_aa</xml>"),
                            "key_signature": "KEY_SIG_AA",
                            "key_certificate": "KEY_CERT_AA",
                        },
                        "invoice": {"error": "XML validation failed by SPV"},
                    },
                },
            ],
            "received_bills_messages": [],
        })

        invoice.invalidate_recordset()

        # Acceptance 'BB' matched by name → index updated, invoice validated
        self.assertEqual(invoice.l10n_ro_edi_state, "invoice_validated")
        self.assertEqual(invoice.l10n_ro_edi_index, "BB")
        # On validation all previous docs (invoice_sent + invoice_refused) are cleaned up
        self.assertEqual(len(invoice.l10n_ro_edi_document_ids), 1)
        self.assertEqual(invoice.l10n_ro_edi_document_ids.state, "invoice_validated")
        # Refusal 'AA' was skipped: no invoice_refused doc was added by synchronize
        self.assertFalse(
            invoice.l10n_ro_edi_document_ids.filtered(lambda d: d.state == "invoice_refused")
        )
