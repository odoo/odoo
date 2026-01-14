from contextlib import contextmanager
import json
from lxml import etree
import requests

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import PatchRequestsMixin
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_hr_edi.tests.test_hr_edi_common import TestL10nHrEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestHrEdiFlowsMocked(TestL10nHrEdiCommon, TestAccountMoveSendCommon, PatchRequestsMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data['company']
        company.write({
            'l10n_hr_mer_username': '...',
            'l10n_hr_mer_password': '...',
            'l10n_hr_mer_company_ident': '12345678',
            'l10n_hr_mer_software_ident': 'Saodoo-001',
            'l10n_hr_mer_connection_state': 'active',
        })

    def assertRequestsEqual(self, actual_request, expected_request):
        """ Override so that when we check the arguments to `requests.Session.request`,
            we use `assertXmlTreeEqual` on the XML documents passed as argument, to benefit
            from ___ignore___ and better error messages.
        """

        if (
            (actual_file := actual_request.get('json', {}).get('File'))
            and (expected_file := expected_request.get('json', {}).get('File'))
        ):
            @contextmanager
            def restore_files():
                try:
                    actual_request['json']['File'] = expected_request['json']['File'] = 'Placeholder for comparison'
                    yield
                finally:
                    actual_request['json']['File'] = actual_file
                    expected_request['json']['File'] = expected_file

            with restore_files():
                super().assertRequestsEqual(actual_request, expected_request)
                self.assertXmlTreeEqual(
                    etree.fromstring(actual_file.encode()),
                    etree.fromstring(expected_file.encode())
                )
        else:
            super().assertRequestsEqual(actual_request, expected_request)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_base_url(self):
        return 'https://demo.moj-eracun.hr'

    def _build_request(self, endpoint, request_args=None):
        return {
            'method': 'post',
            'url': self._get_base_url() + endpoint,
            'headers': {'charset': 'utf-8', 'content-type': 'application/json'},
            'data': None,
            'json': {
                'Username': self.env.company.l10n_hr_mer_username,
                'Password': self.env.company.l10n_hr_mer_password,
                'CompanyId': self.env.company.l10n_hr_mer_company_ident,
                'SoftwareId': self.env.company.l10n_hr_mer_software_ident,
                **(request_args or {}),
            },
            'timeout': 30,
        }

    def _build_response(self, status_code, response_json=None, response_content=None):
        response = requests.Response()
        response.status_code = status_code
        if response_json is not None:
            response._content = json.dumps(response_json).encode()
        elif response_content is not None:
            response._content = response_content
        return response

    # -------------------------------------------------------------------------
    # Sending flow
    # -------------------------------------------------------------------------

    def test_10_send_invoice(self):
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_hr_alt(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_IN_ROC_25')

        # 1. Create invoice

        invoice = self.env['account.move'].create({
            'invoice_date': '2025-01-01',
            'date': '2025-01-01',
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()

        self.assertRecordValues(invoice, [{
            'l10n_hr_process_type': 'P1',
            'l10n_hr_fiscal_user_id': self.env.user.partner_id.id,
            'l10n_hr_operator_name': 'Because I am accountman!',
            'l10n_hr_operator_oib': '01234567896',
        }])

        # 2. Send invoice to MER

        send_and_print = self.create_send_and_print(invoice)

        with file_open('l10n_hr_edi/tests/flows/out_invoice.xml', 'r') as f:
            expected_invoice_xml = f.read()

        with self.assertRequests([
            (
                # Request 1: Send invoice
                self._build_request(
                    endpoint='/apis/v2/send',
                    request_args={
                        'File': expected_invoice_xml,
                    },
                ),
                self._build_response(
                    status_code=200,
                    response_json={
                        'ElectronicId': '3083666',
                        'DocumentNr': invoice.name,
                        'DocumentTypeId': 1,
                        'DocumentTypeName': 'Račun',
                        'StatusId': 20,
                        'StatusName': 'Obrađen',
                        'RecipientBusinessNumber': 'BE0477472701',
                        'RecipientBusinessUnit': '',
                        'RecipientBusinessName': 'Odoo S.A.',
                        'Created': '2025-10-14T14:27:06.2388492+02:00',
                        'Sent': '2025-10-14T14:27:06.3355877+02:00',
                        'Modified': '2025-10-14T14:27:06.3355877+02:00',
                        'Delivered': None,
                    }
                ),
            ),
        ]):
            send_and_print._generate_and_send_invoices(invoice)

        self.assertRecordValues(invoice, [{
            'l10n_hr_mer_document_status': '20',
            'l10n_hr_mer_document_eid': '3083666',
        }])

    def test_send_invoice_error(self):
        self.setup_partner_as_hr(self.env.company.partner_id)
        self.setup_partner_as_hr_alt(self.partner_a)
        tax = self.env['account.chart.template'].ref('VAT_S_IN_ROC_25')

        # 1. Create invoice

        invoice = self.env['account.move'].create({
            'invoice_date': '2025-01-01',
            'date': '2025-01-01',
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ],
        })
        invoice.action_post()

        self.assertRecordValues(invoice, [{
            'l10n_hr_process_type': 'P1',
            'l10n_hr_fiscal_user_id': self.env.user.partner_id.id,
            'l10n_hr_operator_name': 'Because I am accountman!',
            'l10n_hr_operator_oib': '01234567896',
        }])

        # 2. Send invoice to MER

        send_and_print = self.create_send_and_print(invoice)

        with file_open('l10n_hr_edi/tests/flows/out_invoice.xml', 'r') as f:
            expected_invoice_xml = f.read()

        with self.assertRaisesRegex(UserError, 'Korisničko ime i lozinka nisu ispravni.. Trace ID: 4f701362-96cc-49c6-a297-854e740ad719.'):
            with self.assertRequests([
                (
                    # Request 1: Send invoice
                    self._build_request(
                        endpoint='/apis/v2/send',
                        request_args={
                            'File': expected_invoice_xml,
                        },
                    ),
                    self._build_response(
                        status_code=200,
                        response_json={
                            'Username':
                                {
                                    'Value': 'Incorrect',
                                    'Messages': ['Korisničko ime i lozinka nisu ispravni.. Trace ID: 4f701362-96cc-49c6-a297-854e740ad719.']
                                }
                            }
                    ),
                ),
            ]):
                send_and_print._generate_and_send_invoices(invoice)

    # -------------------------------------------------------------------------
    # Receiving flow
    # -------------------------------------------------------------------------

    def test_20_receive_invoice(self):
        self.setup_partner_as_hr(self.env.company.partner_id)

        # 1. Fetch inbound invoices

        with file_open('l10n_hr_edi/tests/flows/in_invoice.xml', 'rb') as f:
            mocked_in_invoice_bytes = f.read()

        with self.assertRequests([
            (
                # Request 1: queryInbox
                self._build_request(endpoint='/apis/v2/queryInbox'),
                self._build_response(
                    status_code=200,
                    response_json=[{
                        'ElectronicId': 3148006,
                        'DocumentNr': '2/1/1',
                        'DocumentTypeId': 1,
                        'DocumentTypeName': 'Račun',
                        'StatusId': 40,
                        'StatusName': 'Preuzet',
                        'SenderBusinessNumber': 'BE0477472701',
                        'SenderBusinessUnit': None,
                        'SenderBusinessName': 'Odoo S.A.',
                        'Updated': '2025-12-29T09:37:04.5605292',
                        'Sent': '2025-12-24T10:31:17.5989975',
                        'Delivered': '2025-12-29T09:37:04.5605231',
                        'Imported': False
                    }]
                )
            ),
            (
                # Request 2: statusInbox
                self._build_request(
                    endpoint='/api/fiscalization/statusInbox',
                    request_args={
                        'ElectronicId': '3148006',
                    }
                ),
                self._build_response(
                    status_code=200,
                    response_json=[{
                        'electronicId': 762506406,
                        'senderName': 'Mock d.o.o.',
                        'senderIdentifierValue': '12345678901',
                        'channelType': 1,
                        'channelTypeDescription': 'eIzvještavanje',
                        'businessStatusReason': 'Mock business status reason',
                        'messages': [{
                            'status': 0,
                            'statusDescription': 'Uspjeh',
                            'fiscalizationRequestId': '73743778-d386-466b-938f-020831fa9092',
                            'dateOfFiscalization': '2025-12-29T16:15:29.3745898+01:00',
                            'message': 'Mock fiscalization successful',
                            'encodedXml': 'TW9jayBYTUwgY29udGVudCBmb3IgZmlzY2FsaXphdGlvbiBzdGF0dXMgcmVzcG9uc2U=',
                            'errorCode': 'S001',
                            'errorCodeDescription': 'Sistemska greška prilikom obrade zahtjeva',
                            'messageType': 0,
                            'messageTypeDescription': 'Kao POŠILJATELJ dohvati status fiskalizacijske poruke'
                        }]
                    }]
                )
            ),
            (
                # Request 3: queryDocumentProcessStatusInbox
                self._build_request(
                    endpoint='/apis/v2/queryDocumentProcessStatusInbox',
                    request_args={
                        'ElectronicId': '3148006',
                    }
                ),
                self._build_response(
                    status_code=200,
                    response_json=[{
                        'ElectronicId': 3148006,
                        'DocumentNr': '2/1/1',
                        'DocumentTypeId': 1,
                        'DocumentTypeName': 'Račun',
                        'StatusId': 40,
                        'StatusName': 'Preuzet',
                        'SenderBusinessNumber': 'BE0477472701',
                        'SenderBusinessUnit': None,
                        'SenderBusinessName': 'Odoo S.A.',
                        'Sent': '2025-12-24T10:31:17.5989975',
                        'Delivered': '2025-12-29T09:37:04.5605231',
                        'IssueDate': '2025-12-24T00:00:00',
                        'DocumentProcessStatusId': 4,
                        'DocumentProcessStatusName': 'Potvrda zaprimanja',
                        'AdditionalDokumentStatusId': None,
                        'RejectReason': None,
                        'InboundFiscalizationStatus': None
                    }]
                )
            ),
            (
                # Request 4: receive
                self._build_request(
                    endpoint='/apis/v2/receive',
                    request_args={
                        'ElectronicId': '3148006',
                    }
                ),
                self._build_response(
                    status_code=200,
                    response_content=mocked_in_invoice_bytes
                )
            ),
        ]):
            self.company_data['default_journal_purchase'].l10n_hr_mer_get_new_documents_all()

        fetched_invoice = self.env['account.move'].search([('l10n_hr_mer_document_eid', '=', '3148006')])

        self.assertRecordValues(fetched_invoice, [{
            'ref': '2/1/1',
            'payment_reference': 'HR00 211',
            'invoice_date': fields.Date.from_string('2025-12-24'),
            'invoice_date_due': fields.Date.from_string('2025-12-24'),
            'amount_untaxed': 47.0,
            'amount_tax': 6.11,
            'amount_total': 53.11,
            'l10n_hr_mer_document_eid': '3148006',
            'l10n_hr_mer_document_status': '40',
            'l10n_hr_process_type': 'P1',
            'l10n_hr_business_document_status': '4',
            'l10n_hr_fiscalization_number': '2/1/1',
            'l10n_hr_fiscalization_status': '0',
            'l10n_hr_fiscalization_error': 'S001 - Sistemska greška prilikom obrade zahtjeva',
            'l10n_hr_fiscalization_request': '73743778-d386-466b-938f-020831fa9092',
            'l10n_hr_fiscalization_channel_type': '1',
        }])

        self.assertRecordValues(fetched_invoice.partner_id, [{
            'name': 'HR Company',
            'vat': 'HR18724543544',
            'street': 'Vukasi',
            'city': 'Ježdovec',
            'zip': '10250',
            'country_id': self.env.ref('base.hr').id,
        }])

        self.assertRecordValues(fetched_invoice.invoice_line_ids, [{
            'name': '[E-COM10] Pedal Bin',
            'quantity': 1.0,
            'price_unit': 47.0,
        }])

        self.assertEqual(fetched_invoice.invoice_line_ids.tax_ids.amount, 13.0)
