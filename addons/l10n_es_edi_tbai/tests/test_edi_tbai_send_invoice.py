from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommonGipuzkoa
import base64
from lxml import etree


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSendAndPrintEdiGipuzkoa(TestEsEdiTbaiCommonGipuzkoa):

    def test_post_and_cancel_invoice_tbai_success(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        self.assertEqual(invoice.l10n_es_tbai_state, 'to_send')
        self.assertFalse(invoice.l10n_es_tbai_chain_index)
        self.assertFalse(invoice.l10n_es_tbai_post_document_id.xml_attachment_id)

        # Post with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        self.assertEqual(invoice.l10n_es_tbai_state, 'sent')
        self.assertTrue(invoice.l10n_es_tbai_chain_index)
        self.assertEqual(invoice.l10n_es_tbai_post_document_id.state, 'accepted')
        self.assertTrue(invoice.l10n_es_tbai_post_document_id.xml_attachment_id)

        self.assertEqual(invoice.state, 'posted')
        self.assertFalse(invoice.l10n_es_tbai_cancel_document_id.xml_attachment_id)

        # Cancel with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_cancel_invoice_success,
        ):
            invoice.l10n_es_tbai_cancel()

        self.assertEqual(invoice.l10n_es_tbai_state, 'cancelled')
        self.assertEqual(invoice.l10n_es_tbai_cancel_document_id.state, 'accepted')
        self.assertTrue(invoice.l10n_es_tbai_cancel_document_id.xml_attachment_id)

        self.assertEqual(invoice.state, 'cancel')

    def test_post_invoice_tbai_failure(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        # Post with error
        # In a non-test environment, the changes would be commited before raising the UserError,
        # here we have to catch it in order to keep them.
        try:
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                return_value=self.mock_response_failure,
            ):
                invoice_send_wizard.action_send_and_print()
            raise AssertionError("A UserError should have been raised.")

        except UserError:
            self.assertEqual(invoice.l10n_es_tbai_state, 'to_send')
            self.assertFalse(invoice.l10n_es_tbai_chain_index)
            self.assertEqual(invoice.l10n_es_tbai_post_document_id.state, 'rejected')
            self.assertTrue(invoice.l10n_es_tbai_post_document_id.xml_attachment_id)

        failed_document_id = invoice.l10n_es_tbai_post_document_id.id

        # Post with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        self.assertNotEqual(invoice.l10n_es_tbai_post_document_id.id, failed_document_id)

        self.assertEqual(invoice.l10n_es_tbai_state, 'sent')
        self.assertTrue(invoice.l10n_es_tbai_chain_index)
        self.assertEqual(invoice.l10n_es_tbai_post_document_id.state, 'accepted')
        self.assertTrue(invoice.l10n_es_tbai_post_document_id.xml_attachment_id)

    def test_cancel_invoice_tbai_failure(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        # Post with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        # Cancel with error
        try:
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                return_value=self.mock_response_failure,
            ):
                invoice.l10n_es_tbai_cancel()
            raise AssertionError("A UserError should have been raised.")

        except UserError:
            self.assertEqual(invoice.l10n_es_tbai_state, 'sent')
            self.assertEqual(invoice.l10n_es_tbai_cancel_document_id.state, 'rejected')
            self.assertTrue(invoice.l10n_es_tbai_cancel_document_id.xml_attachment_id)

        failed_document_id = invoice.l10n_es_tbai_cancel_document_id.id

        # Cancel with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_cancel_invoice_success,
        ):
            invoice.l10n_es_tbai_cancel()

        self.assertNotEqual(invoice.l10n_es_tbai_cancel_document_id.id, failed_document_id)

        self.assertEqual(invoice.l10n_es_tbai_state, 'cancelled')
        self.assertEqual(invoice.l10n_es_tbai_cancel_document_id.state, 'accepted')
        self.assertTrue(invoice.l10n_es_tbai_cancel_document_id.xml_attachment_id)

    def test_post_invoice_tbai_request_error(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        # Post with request error
        try:
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                side_effect=self.mock_request_error,
            ):
                invoice_send_wizard.action_send_and_print()
            raise AssertionError("A UserError should have been raised.")

        except UserError:
            self.assertEqual(invoice.l10n_es_tbai_state, 'to_send')
            self.assertTrue(invoice.l10n_es_tbai_chain_index)
            self.assertEqual(invoice.l10n_es_tbai_post_document_id.state, 'to_send')
            self.assertTrue(invoice.l10n_es_tbai_post_document_id.xml_attachment_id)

        pending_document_id = invoice.l10n_es_tbai_post_document_id.id
        chain_index = invoice.l10n_es_tbai_chain_index

        # Post with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        self.assertEqual(invoice.l10n_es_tbai_post_document_id.id, pending_document_id)
        self.assertEqual(invoice.l10n_es_tbai_chain_index, chain_index)

        self.assertEqual(invoice.l10n_es_tbai_state, 'sent')
        self.assertEqual(invoice.l10n_es_tbai_post_document_id.state, 'accepted')
        self.assertTrue(invoice.l10n_es_tbai_post_document_id.xml_attachment_id)

    def test_cancel_invoice_request_error(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        # Post with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        # Cancel with request error
        try:
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                side_effect=self.mock_request_error,
            ):
                invoice.l10n_es_tbai_cancel()
            raise AssertionError("A UserError should have been raised.")

        except UserError:
            self.assertEqual(invoice.l10n_es_tbai_state, 'sent')
            self.assertEqual(invoice.l10n_es_tbai_cancel_document_id.state, 'to_send')
            self.assertTrue(invoice.l10n_es_tbai_cancel_document_id.xml_attachment_id)

        pending_document_id = invoice.l10n_es_tbai_cancel_document_id.id

        # Cancel with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_cancel_invoice_success,
        ):
            invoice.l10n_es_tbai_cancel()

        self.assertEqual(invoice.l10n_es_tbai_cancel_document_id.id, pending_document_id)

        self.assertEqual(invoice.l10n_es_tbai_state, 'cancelled')
        self.assertEqual(invoice.l10n_es_tbai_cancel_document_id.state, 'accepted')
        self.assertTrue(invoice.l10n_es_tbai_cancel_document_id.xml_attachment_id)

    def test_tbai_credit_note_importe_total(self):
        invoice = self._create_posted_invoice()

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            self._get_invoice_send_wizard(invoice).action_send_and_print()

            reversal = self.env['account.move.reversal'].with_context(
                active_model="account.move", active_ids=invoice.ids
            ).create({
                'journal_id': invoice.journal_id.id,
                'l10n_es_tbai_refund_reason': 'R4',
            })
            credit_note = self.env['account.move'].browse(reversal.refund_moves()['res_id'])
            credit_note.action_post()

            self._get_invoice_send_wizard(credit_note).action_send_and_print()

        tbai_xml = base64.b64decode(credit_note['l10n_es_tbai_post_file']).decode()
        value = etree.fromstring(tbai_xml).findtext(".//ImporteTotalFactura")
        self.assertEqual(value, '-4840.00')
