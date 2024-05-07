from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommonBizkaia


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSendAndPrintEdiBizkaia(TestEsEdiTbaiCommonBizkaia):
    """
    All the ticketbai document logic is tested with TestSendAndPrintEdiGipuzkoa,
    as Bizkaia and Gipuzokoa only differs by the requests,
    only the request logic is tested here.
    """

    def test_post_and_cancel_invoice_tbai_success(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        # Post with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        self.assertEqual(invoice.l10n_es_tbai_state, 'sent')

        # Cancel with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_cancel_invoice_success,
        ):
            invoice.l10n_es_tbai_cancel()

        self.assertEqual(invoice.l10n_es_tbai_state, 'cancelled')

    def test_post_invoice_tbai_failure(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        # Post with error
        try:
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                return_value=self.mock_response_post_invoice_failure,
            ):
                invoice_send_wizard.action_send_and_print()
            raise AssertionError("A UserError should have been raised.")

        except UserError:
            self.assertEqual(invoice.l10n_es_tbai_state, 'to_send')

        # Post with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        self.assertEqual(invoice.l10n_es_tbai_state, 'sent')

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
                return_value=self.mock_response_cancel_invoice_failure,
            ):
                invoice.l10n_es_tbai_cancel()
            raise AssertionError("A UserError should have been raised.")

        except UserError:
            self.assertEqual(invoice.l10n_es_tbai_state, 'sent')

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
