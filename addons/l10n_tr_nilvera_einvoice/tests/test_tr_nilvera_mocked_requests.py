import re
from functools import wraps
from io import BytesIO
from unittest.mock import MagicMock, call, patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_tr_nilvera_einvoice.tests.test_xml_ubl_tr_common import TestUBLTRCommon

COMPANY_VAT = '3297552117'
ERRORENOUS_ALIAS = 'erroneous_alias'
EINVOICE_PARTNER_VAT = '1729171602'
EARCHIVE_PARTNER_VAT = '17291716060'
SERVER_ERROR_ALIAS = 'server_error_alias'
UNAUTHORIZED_ALIAS = 'unauthorized_alias'
UUID_INVALID_STATUS = 'uuid_with_invalid_status_code'
UUID_INVALID_INVOICE = 'uuid_invalid_invoice'
UUID_VALID_INVOICE = 'uuid_valid_invoice'


def mock_requests_request(method, url, *args, **kwargs):
    response = MagicMock()
    response.status_code = 200

    if method == 'GET' and 'Check/TaxNumber' in url:
        if EINVOICE_PARTNER_VAT in url:
            response.json.return_value = [
                {
                    'DocumentType': 'Invoice',
                    'Name': 'urn:mail:salt@bae.com',
                    'TaxNumber': EINVOICE_PARTNER_VAT,
                    'Title': 'Salt Bae LLC',
                    'Type': 'OZEL',
                }
            ]
        elif COMPANY_VAT in url:
            response.json.return_value = [
                {
                    'TaxNumber': 'text',
                    'Title': 'text',
                    'FirstCreatedTime': '2025-06-23',
                    'CreationTime': '2025-06-23',
                    'DocumentType': 'text',
                    'Name': 'text',
                    'Type': 'text',
                }
            ]
        elif EARCHIVE_PARTNER_VAT in url:
            response.json.return_value = []

    elif method == 'GET' and (match := re.fullmatch(r'/einvoice/sale/([\w-]+)/Status', url)):
        if match.group(1) == UUID_INVALID_STATUS:
            data = {
                "InvoiceStatus": {
                    "Code": "boop",
                    "Description": "text",
                    "DetailDescription": "text",
                },
            }
            response.get.side_effect = data.get
        else:
            data = {
                "InvoiceStatus": {
                    "Code": "succeed",
                    "Description": "text",
                    "DetailDescription": "text",
                },
            }
            response.get.side_effect = data.get

    elif method == 'POST' and 'Send/Xml' in url:
        if UNAUTHORIZED_ALIAS in url:
            response.status_code = 401
            response.text = 'Unauthorized'
        elif SERVER_ERROR_ALIAS in url:
            response.status_code = 500
            response.text = 'Internal Server Error'
        elif ERRORENOUS_ALIAS in url:
            response.status_code = 422
            response.json.return_value = {
                "Message": "HATALI ISTEK",
                "Errors": [{
                    "Code": 2000,
                    "Description": "Yeterli Kontörünüz Bulunmamaktadır.",
                    "Detail": "Yeterli Kontörünüz Bulunmamaktadır. Lütfen Kontör Alımı Yapınız.",
                }]
            }
        else:
            response.json.return_value = {
                "UUID": "00aac88a-576b-4a62-98b5-ed34fe4d187d",
                "InvoiceNumber": "",
            }

    elif method == 'GET' and '/einvoice/Purchase' in url:
        if '/xml' in url:
            with file_open('l10n_tr_nilvera_einvoice/tests/test_files/fetching/invoice.xml', 'rb') as xml:
                response = xml.read()
        elif '/pdf' in url:
            with file_open('l10n_tr_nilvera_einvoice/tests/test_files/fetching/invoice.pdf', 'rb') as pdf:
                response = pdf.read()
        else:
            response.get.return_value = [
                {'UUID': 'invoice_uuid'},
            ]
    return response


def patch_nilvera_request(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        with patch(
            'odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request',
            side_effect=mock_requests_request
        ) as mocked_request:
            # If the test expects the mock as an argument, pass it
            if 'mocked_request' in function.__code__.co_varnames:
                return function(*args, mocked_request, **kwargs)
            else:
                return function(*args, **kwargs)
    return wrapper


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTRNilveraMockedRequests(TestUBLTRCommon):

    @classmethod
    @patch_nilvera_request
    def setUpClass(cls):
        super().setUpClass()
        # Needed to ensure the partners are fully initialized before tests run (i.e. this ends up calling the Nilvera mock API to validate some fields)
        cls.env.context = {**cls.env.context, 'l10n_tr_nilvera_use_mock': True}
        cls.einvoice_partner.flush_recordset()
        cls.earchive_partner.flush_recordset()

    @patch_nilvera_request
    def test_which_service_to_call(self):
        _, invoice = self._generate_invoice_xml(self.einvoice_partner, include_invoice=True)

        invoices_data = {
            invoice: {**invoice.read()[0], 'extra_edis': {'tr_nilvera'}}
        }

        with patch('odoo.addons.l10n_tr_nilvera_einvoice.models.account_move.AccountMove._l10n_tr_nilvera_submit_einvoice') as mock_submit_einvoice, \
             patch('odoo.addons.l10n_tr_nilvera_einvoice.models.account_move.AccountMove._l10n_tr_nilvera_submit_earchive') as mock_submit_earchive:
            self.env['account.move.send']._call_web_service_before_invoice_pdf_render(invoices_data)
            mock_submit_einvoice.assert_called_once()
            mock_submit_earchive.assert_not_called()

            # Reset the alias to empty for the next test
            invoice.partner_id.l10n_tr_nilvera_customer_alias_id = self.env['l10n_tr.nilvera.alias']
            invoice.partner_id.vat = False
            mock_submit_einvoice.reset_mock()
            mock_submit_earchive.reset_mock()

            self.env['account.move.send']._call_web_service_before_invoice_pdf_render(invoices_data)
            mock_submit_earchive.assert_called_once()
            mock_submit_einvoice.assert_not_called()

    @patch_nilvera_request
    def test_submit_einvoice(self, mocked_request):
        xml, invoice = self._generate_invoice_xml(self.einvoice_partner, include_invoice=True)
        wrapped_xml = BytesIO(xml)
        wrapped_xml.name = 'invoice.xml'
        invoice._l10n_tr_nilvera_submit_einvoice(wrapped_xml, self.einvoice_partner.l10n_tr_nilvera_customer_alias_id.name)

        mocked_request.assert_called_once_with(
            'POST',
            '/einvoice/Send/Xml?Alias=urn%3Amail%3Asalt%40bae.com',
            files={'file': ('invoice.xml', wrapped_xml, 'application/xml')},
            handle_response=False,
        )
        self.assertTrue(invoice.is_move_sent)
        self.assertEqual(invoice.l10n_tr_nilvera_send_status, 'sent')

    @patch_nilvera_request
    def test_submit_earchive(self, mocked_request):
        xml, invoice = self._generate_invoice_xml(self.earchive_partner, include_invoice=True)
        wrapped_xml = BytesIO(xml)
        wrapped_xml.name = 'invoice.xml'
        invoice._l10n_tr_nilvera_submit_earchive(wrapped_xml)

        mocked_request.assert_called_once_with(
            'POST',
            '/earchive/Send/Xml',
            files={'file': ('invoice.xml', wrapped_xml, 'application/xml')},
            handle_response=False,
        )

        self.assertTrue(invoice.is_move_sent)
        self.assertEqual(invoice.l10n_tr_nilvera_send_status, 'sent')

    @patch_nilvera_request
    def test_submit_einvoice_errors(self):
        xml, invoice = self._generate_invoice_xml(self.einvoice_partner, include_invoice=True)
        wrapped_xml = BytesIO(xml)
        wrapped_xml.name = 'invoice.xml'
        error_cases = [
            (UNAUTHORIZED_ALIAS, "Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera."),
            (SERVER_ERROR_ALIAS, "Server error from Nilvera, please try again later."),
            (ERRORENOUS_ALIAS, "The invoice couldn't be sent due to the following errors:\n2000 - Yeterli Kontörünüz Bulunmamaktadır.: Yeterli Kontörünüz Bulunmamaktadır. Lütfen Kontör Alımı Yapınız.\n"),
        ]

        for alias, expected_error in error_cases:
            with self.assertRaises(UserError) as context:
                invoice._l10n_tr_nilvera_submit_einvoice(wrapped_xml, alias)
            self.assertEqual(str(context.exception), expected_error)

    @patch_nilvera_request
    def test_fetch_status(self):
        _, invoice = self._generate_invoice_xml(self.einvoice_partner, include_invoice=True)
        invoice._l10n_tr_nilvera_get_submitted_document_status()

        self.assertEqual(invoice.l10n_tr_nilvera_send_status, 'succeed')

    @patch_nilvera_request
    def test_fetch_invalid_status(self):
        _, invoice = self._generate_invoice_xml(self.einvoice_partner, include_invoice=True)
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
                call('GET', '/einvoice/Purchase', params={'StatusCode': ['succeed']}),
                call('GET', '/einvoice/Purchase/invoice_uuid/xml', params={'StatusCode': ['succeed']}),
                call('GET', '/einvoice/Purchase/invoice_uuid/pdf'),
                call('GET', '/einvoice/Purchase', params={'StatusCode': ['succeed']}),
            ])

            invoice = self.env['account.move'].search([('l10n_tr_nilvera_uuid', '=', 'invoice_uuid')])
            self.assertEqual(len(invoice), 1)
            self.assertListEqual(sorted(invoice.attachment_ids.mapped('mimetype')), ['application/pdf', 'application/xml'])
