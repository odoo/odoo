from odoo import Command
from odoo.addons.l10n_tr_nilvera_einvoice.tests.common import (
    ERRORENOUS_ALIAS,
    SERVER_ERROR_ALIAS,
    UNAUTHORIZED_ALIAS,
    UUID_INVALID_STATUS,
    TrNilveraCommon,
    patch_nilvera_request,
)
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

from freezegun import freeze_time
from unittest.mock import call, patch


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTRNilveraEInvoice(TrNilveraCommon):

    @freeze_time('2025-06-24')
    def test_generate_xml(self):
        xml, _ = self._generate_invoice_xml()

        with file_open('l10n_tr_nilvera_einvoice/tests/test_files/invoice.xml', 'rb') as expected_file:
            expected_xml = expected_file.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(xml.read()),
            self.get_xml_tree_from_string(expected_xml),
        )

    def test_which_service_to_call(self):
        xml, invoice = self._generate_invoice_xml()
        wizard = self.env['account.move.send'].create({
            'move_ids': [Command.set(invoice.ids)],
            'l10n_tr_nilvera_einvoice_checkbox_xml': True,
        })
        invoice.ubl_cii_xml_id = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'raw': xml.getvalue(),
            'res_model': 'account.move',
            'res_id': invoice.id,
        })

        invoice_data = {
            invoice: {
                **(wizard._get_wizard_values()),
            }
        }

        with patch('odoo.addons.l10n_tr_nilvera_einvoice.models.account_move.AccountMove._l10n_tr_nilvera_submit_einvoice') as mock_submit_einvoice, \
             patch('odoo.addons.l10n_tr_nilvera_einvoice.models.account_move.AccountMove._l10n_tr_nilvera_submit_earchive') as mock_submit_earchive:
            wizard._call_web_service_before_invoice_pdf_render(invoice_data)
            mock_submit_einvoice.assert_called_once()
            mock_submit_earchive.assert_not_called()

            # Reset the alias to empty for the next test
            invoice.partner_id.l10n_tr_nilvera_customer_alias_id = self.env['l10n_tr.nilvera.alias']
            invoice.partner_id.vat = False
            mock_submit_einvoice.reset_mock()
            mock_submit_earchive.reset_mock()

            wizard._call_web_service_before_invoice_pdf_render(invoice_data)
            mock_submit_earchive.assert_called_once()
            mock_submit_einvoice.assert_not_called()

    @patch_nilvera_request
    def test_submit_einvoice(self, mocked_request):
        xml, invoice = self._generate_invoice_xml()
        invoice._l10n_tr_nilvera_submit_einvoice(xml, self.partner.l10n_tr_nilvera_customer_alias_id.name)

        mocked_request.assert_called_once_with(
            'POST',
            '/einvoice/Send/Xml?Alias=urn%3Amail%3Asalt%40bae.com',
            files={'file': ('invoice.xml', xml, 'application/xml')},
            handle_response=False,
        )
        self.assertTrue(invoice.is_move_sent)
        self.assertEqual(invoice.l10n_tr_nilvera_send_status, 'sent')

    @patch_nilvera_request
    def test_submit_earchive(self, mocked_request):
        xml, invoice = self._generate_invoice_xml()
        invoice._l10n_tr_nilvera_submit_earchive(xml)

        mocked_request.assert_called_once_with(
            'POST',
            '/earchive/Send/Xml',
            files={'file': ('invoice.xml', xml, 'application/xml')},
            handle_response=False,
        )

        self.assertTrue(invoice.is_move_sent)
        self.assertEqual(invoice.l10n_tr_nilvera_send_status, 'sent')

    @patch_nilvera_request
    def test_submit_einvoice_errors(self):
        xml, invoice = self._generate_invoice_xml()
        error_cases = [
            (UNAUTHORIZED_ALIAS, "Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera."),
            (SERVER_ERROR_ALIAS, "Server error from Nilvera, please try again later."),
            (ERRORENOUS_ALIAS, "The invoice couldn't be sent due to the following errors:\n2000 - Yeterli Kontörünüz Bulunmamaktadır.: Yeterli Kontörünüz Bulunmamaktadır. Lütfen Kontör Alımı Yapınız.\n"),
        ]

        for alias, expected_error in error_cases:
            with self.assertRaises(UserError) as context:
                invoice._l10n_tr_nilvera_submit_einvoice(xml, alias)
            self.assertEqual(str(context.exception), expected_error)

    @patch_nilvera_request
    def test_fetch_status(self):
        _, invoice = self._generate_invoice_xml()
        invoice._l10n_tr_nilvera_get_submitted_document_status()

        self.assertEqual(invoice.l10n_tr_nilvera_send_status, 'succeed')

    @patch_nilvera_request
    def test_fetch_invalid_status(self):
        _, invoice = self._generate_invoice_xml()
        invoice.l10n_tr_nilvera_uuid = UUID_INVALID_STATUS

        invoice._l10n_tr_nilvera_get_submitted_document_status()

        self.assertIn(
            invoice.message_ids[0].preview,
            "The invoice status couldn't be retrieved from Nilvera."
        )

    @patch_nilvera_request
    def test_fetching_einvoices(self, mocked_request):
        with patch.object(self.env.cr, 'commit', autospec=True):
            self.env['account.move']._l10n_tr_nilvera_get_documents()
            self.env['account.move']._l10n_tr_nilvera_get_documents()  # Test that the second time it does not fetch again

            self.assertListEqual(mocked_request.call_args_list, [
                call('GET', '/einvoice/Purchase'),
                call('GET', '/einvoice/Purchase/invoice_uuid/xml'),
                call('GET', '/einvoice/Purchase/invoice_uuid/pdf'),
                call('GET', '/einvoice/Purchase'),
            ])
