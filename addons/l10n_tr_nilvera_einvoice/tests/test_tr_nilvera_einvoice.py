from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open
from odoo.exceptions import UserError

from freezegun import freeze_time
from unittest.mock import patch
from unittest.mock import MagicMock
from io import BytesIO
import re
import base64

PARTNER_VAT = '17291716060'
COMPANY_VAT = '3297552117'
UNAURHORIZED_ALIAS = 'unauthorized_alias'
SERVER_ERROR_ALIAS = 'server_error_alias'
ERRORENOUS_ALIAS = 'erroneous_alias'
UUID_INVALID_STATUS = 'uuid_with_invalid_status_code'
UUID_VALID_INVOICE = 'uuid_valid_invoice'
UUID_INVALID_INVOICE = 'uuid_invalid_invoice'


def mock_requests_request(method, url, *args, **kwargs):
    response = MagicMock()
    response.status_code = 200

    if method == 'GET' and 'Check/TaxNumber' in url:
        if PARTNER_VAT in url:
            response.json.return_value = [
                {
                    'DocumentType': 'Invoice',
                    'Name': 'urn:mail:salt@bae.com',
                    'TaxNumber': '17291716060',
                    'Title': 'Salt Bae LLC',
                    'Type': 'OZEL',
                }
            ]
        elif COMPANY_VAT in url:
            response.json.return_value = [
                {
                    'TaxNumber': 'text',
                    'Title': 'text',
                    'FirstCreatedTime': '2025-06-23T20:21:49.747Z',
                    'CreationTime': '2025-06-23T20:21:49.747Z',
                    'DocumentType': 'text',
                    'Name': 'text',
                    'Type': 'text'
                }
            ]

    if method == 'GET' and (match := re.fullmatch(r'/einvoice/sale/([a-fA-F0-9-]+)/Status', url)):
        if UUID_INVALID_STATUS == match.group(1):
            response = {
                "InvoiceStatus": {
                    "Code": "boop",
                    "Description": "text",
                    "DetailDescription": "text"
                },
            }
        else:
            response = {
                "InvoiceStatus": {
                    "Code": "succeed",
                    "Description": "text",
                    "DetailDescription": "text"
                },
            }

    if method == 'GET' and url.endswith('einvoice/Purchase'):
        response = {
            "Content": [
                {"UUID": UUID_VALID_INVOICE},
                # {"UUID": UUID_INVALID_INVOICE},
            ],
        }

    if method == 'GET' and (match := re.fullmatch(r'/einvoice/Purchase/(.+)/(xml|pdf)', url)):
        if UUID_VALID_INVOICE == match.group(1):
            with file_open(f'l10n_tr_nilvera_einvoice/tests/test_files/invoice.{match.group(2)}', 'rb') as file:
                response = file.read() if match.group(2) == 'xml' else base64.b64encode(file.read()).decode('utf-8')
        elif UUID_INVALID_INVOICE == match.group(1):
            response.text = '<Invoice>Invalid Invoice</Invoice>'
        else:
            response.text = '<Invoice>Unknown Invoice</Invoice>'

    if method == 'POST' and 'Send/Xml' in url:
        if UNAURHORIZED_ALIAS in url:
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
                    "Detail": "Yeterli Kontörünüz Bulunmamaktadır. Lütfen Kontör Alımı Yapınız."
                }]
            }
        else:
            response.json.return_value = {
                "UUID": "00aac88a-576b-4a62-98b5-ed34fe4d187d",
                "InvoiceNumber": ""
            }

    return response


@freeze_time('2025-06-24')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTRNilveraEInvoice(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        with patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request):
            cls.company_data['company'].partner_id.write({
                'vat': '3297552117',
                'street': '3281. Cadde',
                'zip': '06810',
                'city': 'İç Anadolu Bölgesi',
                'state_id': cls.env.ref('base.state_tr_81').id,
                'country_code': 'TR',
                'ref': 'Tax Office',
            })

            cls.partner = cls.env['res.partner'].create({
                'name': 'Salt Bae LLC',
                'vat': '17291716060',
                'street': 'Gökhane Sokak No:1',
                'zip': '06934',
                'city': 'Sincan/Ankara',
                'state_id': cls.env.ref('base.state_tr_06').id,
                'country_id': cls.env.ref('base.tr').id,
                'l10n_tr_nilvera_customer_status': 'einvoice',
                'ubl_cii_format': 'ubl_tr',
                'ref': 'Salt Bae Tax Office',
            })

            cls.partner.flush_recordset()

    def _generate_invoice_xml(self):
        invoice = self.env['account.move'].create({
            'company_id': self.company_data['company'].id,
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'date': '2025-06-24',
            'invoice_date': '2025-06-24',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                }),
            ],
        })

        invoice.action_post()

        generated_xml = BytesIO(self.env['account.edi.xml.ubl.tr']._export_invoice(invoice)[0])
        generated_xml.name = 'invoice.xml'

        return generated_xml, invoice

    def test_generate_xml(self):
        generated_xml, _ = self._generate_invoice_xml()

        with file_open('l10n_tr_nilvera_einvoice/tests/test_files/invoice.xml', 'rb') as expected_file:
            expected_xml = expected_file.read()

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_xml.read()),
            self.get_xml_tree_from_string(expected_xml)
        )

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request)
    def test_which_service_to_call(self, _):
        xml, invoice = self._generate_invoice_xml()
        wizard = self.env['account.move.send'].create({
            'move_ids': [Command.set(invoice.ids)],
            'l10n_tr_nilvera_einvoice_checkbox_xml': xml,
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

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request)
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

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request)
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

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request)
    def test_submit_einvoice_unauthorized(self, _):
        xml, invoice = self._generate_invoice_xml()
        with self.assertRaises(UserError) as context:
            invoice._l10n_tr_nilvera_submit_einvoice(xml, UNAURHORIZED_ALIAS)

        self.assertEqual(str(context.exception), "Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera.")

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request)
    def test_submit_einvoice_internal_error(self, _):
        xml, invoice = self._generate_invoice_xml()
        with self.assertRaises(UserError) as context:
            invoice._l10n_tr_nilvera_submit_einvoice(xml, SERVER_ERROR_ALIAS)

        self.assertEqual(str(context.exception), "Server error from Nilvera, please try again later.")

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request)
    def test_submit_einvoice_errors(self, _):
        xml, invoice = self._generate_invoice_xml()
        with self.assertRaises(UserError) as context:
            invoice._l10n_tr_nilvera_submit_einvoice(xml, ERRORENOUS_ALIAS)

        self.assertEqual(str(context.exception), "The invoice couldn't be sent due to the following errors:\n2000 - Yeterli Kontörünüz Bulunmamaktadır.: Yeterli Kontörünüz Bulunmamaktadır. Lütfen Kontör Alımı Yapınız.\n")

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request)
    def test_fetch_status(self, _):
        _, invoice = self._generate_invoice_xml()
        invoice._l10n_tr_nilvera_get_submitted_document_status()

        self.assertEqual(invoice.l10n_tr_nilvera_send_status, 'succeed')

    @patch('odoo.addons.l10n_tr_nilvera.lib.nilvera_client.NilveraClient.request', side_effect=mock_requests_request)
    def test_fetch_invalid_status(self, _):
        _, invoice = self._generate_invoice_xml()
        invoice.l10n_tr_nilvera_uuid = UUID_INVALID_STATUS

        invoice._l10n_tr_nilvera_get_submitted_document_status()

        self.assertIn(
            invoice.message_ids[0].preview,
            "The invoice status couldn't be retrieved from Nilvera."
        )
