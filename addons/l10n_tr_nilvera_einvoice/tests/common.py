import re
from functools import wraps
from io import BytesIO
from unittest.mock import MagicMock, patch

from odoo import Command
from odoo.tools import file_open
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

COMPANY_VAT = '3297552117'
ERRORENOUS_ALIAS = 'erroneous_alias'
PARTNER_VAT = '17291716060'
SERVER_ERROR_ALIAS = 'server_error_alias'
UNAUTHORIZED_ALIAS = 'unauthorized_alias'
UUID_INVALID_STATUS = 'uuid_with_invalid_status_code'
UUID_INVALID_INVOICE = 'uuid_invalid_invoice'
UUID_VALID_INVOICE = 'uuid_valid_invoice'


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

    elif method == 'GET' and (match := re.fullmatch(r'/einvoice/sale/([\w-]+)/Status', url)):
        if match.group(1) == UUID_INVALID_STATUS:
            data = {
                "InvoiceStatus": {
                    "Code": "boop",
                    "Description": "text",
                    "DetailDescription": "text"
                },
            }
            response.get.side_effect = data.get
        else:
            data = {
                "InvoiceStatus": {
                    "Code": "succeed",
                    "Description": "text",
                    "DetailDescription": "text"
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
                    "Detail": "Yeterli Kontörünüz Bulunmamaktadır. Lütfen Kontör Alımı Yapınız."
                }]
            }
        else:
            response.json.return_value = {
                "UUID": "00aac88a-576b-4a62-98b5-ed34fe4d187d",
                "InvoiceNumber": ""
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


class TrNilveraCommon(AccountTestInvoicingCommon):

    @classmethod
    @patch_nilvera_request
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].partner_id.write({
            'vat': '3297552117',
            'street': '3281. Cadde',
            'zip': '06810',
            'city': 'İç Anadolu Bölgesi',
            'state_id': cls.env.ref('base.state_tr_81').id,
            'country_code': 'TR',
            'ref': 'Tax Office',
            'bank_ids': [Command.create({'acc_number': 'TR0123456789'})],
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

        # Needed to ensure the partner is fully initialized before tests run (i.e. this ends up calling the Nilvera mock)
        cls.partner.flush_recordset()

    def _generate_invoice_xml(self, **invoice_vals):
        # Returns: (BytesIO, account.move): The generated XML and the invoice record.
        default_vals = {
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
        }
        default_vals.update(invoice_vals)
        invoice = self.env['account.move'].create(default_vals)
        invoice.action_post()

        generated_xml = BytesIO(self.env['account.edi.xml.ubl.tr']._export_invoice(invoice)[0])
        generated_xml.name = 'invoice.xml'

        return generated_xml, invoice
