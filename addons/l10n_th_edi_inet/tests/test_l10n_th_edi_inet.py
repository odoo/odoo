from contextlib import contextmanager
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

import requests
from lxml import etree

from odoo.exceptions import UserError
from odoo.tests import Form, freeze_time, tagged
from odoo.tools import file_open, hash_sign

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon

SIGNED = {'status': 'OK', 'transactionCode': 'TX1', 'xmlURL': 'https://inet/xml', 'pdfURL': 'https://inet/pdf'}


@freeze_time('2026-10-01')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nThEdiInet(AccountTestInvoicingHttpCommon):

    @classmethod
    @AccountTestInvoicingHttpCommon.setup_country('th')
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({
            'l10n_th_is_vat_registered': True,
            'vat': '0105561072420',
            'street': '1768 New Phetchaburi Road',
            'zip': '10310',
            'l10n_th_edi_subdistrict_code': '101702',
            'l10n_th_edi_inet_authorization_code': 'token',
        })
        cls.partner_a.write({
            'vat': '0105536094318',
            'street': '463/59 Sukhumvit Road',
            'zip': '10110',
            'country_id': cls.env.ref('base.th').id,
        })
        cls.tax_on_payment = cls.env['account.tax'].create({
            'name': 'VAT On Payment',
            'amount': 7.0,
            'type_tax_use': 'sale',
            'tax_exigibility': 'on_payment',
        })

    @contextmanager
    def _mock_inet(self, *responses, files=None):
        """ Answer INET's API calls with the given responses, in order, and collect the calls as (endpoint, fields).
        Files are downloaded from `files` by URL, else are their own URL. """
        responses = list(responses)
        calls = []

        def post(url, files, headers, timeout):
            calls.append((url.removeprefix('https://service-etax.one.th'), {key: value[1] for key, value in files.items()}))
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return Mock(json=Mock(return_value=response))

        def get(url, timeout):
            return Mock(content=(files or {}).get(url, f'signed {url}'.encode()))

        with (
            patch('odoo.addons.l10n_th_edi_inet.models.l10n_th_edi_inet_document.requests.post', side_effect=post),
            patch('odoo.addons.l10n_th_edi_inet.models.l10n_th_edi_inet_document.requests.get', side_effect=get),
        ):
            yield calls
        self.assertFalse(responses, "Not all INET responses were used.")

    def _get_xml_values(self, xml_content, *paths):
        """ Return the texts at the given paths of tag names, ignoring the namespaces. """
        tree = etree.fromstring(xml_content)
        return [
            tree.xpath('//' + '/'.join(f"*[local-name()='{tag}']" for tag in path.split('/')) + '/text()')
            for path in paths
        ]

    def _create_tax_invoice(self, tax=None, **invoice_values):
        invoice = self._create_invoice(
            partner_id=self.partner_a.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=1000.0, tax_ids=tax or self.tax_sale_a)],
            post=True,
            **invoice_values,
        )
        return invoice, invoice.l10n_th_tax_invoice_ids

    def test_send_tax_invoice(self):
        invoice, tax_invoice = self._create_tax_invoice()
        self.assertEqual(tax_invoice.l10n_th_edi_state, 'ready_to_send')

        with self._mock_inet(SIGNED) as calls:
            self.env['account.move.send.wizard'].with_context(active_model=invoice._name, active_ids=invoice.ids).create({}).action_send_and_print()

        self.assertRecordValues(tax_invoice, [{
            'l10n_th_edi_state': 'signed',
            'l10n_th_edi_inet_transaction_code': 'TX1',
            'l10n_th_edi_error': False,
            'l10n_th_edi_rd_state': 'waiting',
        }])
        self.assertEqual(tax_invoice.l10n_th_edi_pdf_file_id.raw.content, b'signed https://inet/pdf')
        self.assertEqual(tax_invoice.l10n_th_edi_pdf_file_id.res_id, invoice.id)
        self.assertFalse(invoice.show_reset_to_draft_button)

        [(endpoint, fields)] = calls
        self.assertEqual(endpoint, '/service/etaxsigndocument')
        self.assertEqual(
            (fields['SellerTaxId'], fields['SellerBranchId'], fields['ServiceCode'], fields['SourceSystem']),
            ('0105561072420', '00000', 'S04', 'Odoo'),
        )
        self.assertEqual(self._get_xml_values(
            fields['XMLContent'],
            'ExchangedDocument/TypeCode', 'ID', 'CitySubDivisionName', 'BuildingNumber', 'TaxTotalAmount', 'GrandTotalAmount',
        ), [
            ['388'],
            ['ER3-2560', tax_invoice.tax_invoice_number, '010556107242000000', '010553609431800000'],
            ['101702'],
            ['1768'],
            ['70.00', '70.00'],
            ['1070.00'],
        ])

    def test_send_tax_invoice_with_exempt_and_withholding_taxes(self):
        ChartTemplate = self.env['account.chart.template']
        invoice = self._create_invoice(
            partner_id=self.partner_a.id,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=1000.0, tax_ids=self.tax_sale_a + ChartTemplate.ref('tax_wht_income_3')),
                self._prepare_invoice_line(price_unit=500.0, tax_ids=ChartTemplate.ref('tax_output_vat_exempted')),
            ],
            post=True,
        )

        with self._mock_inet(SIGNED) as calls:
            invoice.l10n_th_tax_invoice_ids.action_l10n_th_edi_send()

        # The customer withholds its tax when paying: it is not on the tax invoice.
        self.assertEqual(self._get_xml_values(
            calls[0][1]['XMLContent'],
            'ApplicableTradeTax/TypeCode', 'ApplicableTradeTax/BasisAmount', 'TaxTotalAmount', 'GrandTotalAmount',
        ), [
            ['VAT', 'FRE', 'VAT', 'FRE'],
            ['1000.00', '500.00', '1000.00', '500.00'],
            ['70.00', '70.00', '0.00'],
            ['1570.00'],
        ])

    def test_send_receipt_tax_invoice_of_partial_payment(self):
        invoice = self._create_invoice(
            partner_id=self.partner_a.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100.0, tax_ids=self.tax_on_payment)] * 3,
            post=True,
        )
        self._register_payment(invoice, amount=107.0)
        receipt = invoice.l10n_th_tax_invoice_ids
        # The receipt's cash basis entry rounds the base per line and the tax per tax.
        self.assertRecordValues(receipt, [{'total_amount': 106.99, 'vat_amount': 7.0}])

        with self._mock_inet(SIGNED) as calls:
            receipt.action_l10n_th_edi_send()

        self.assertEqual(receipt.l10n_th_edi_state, 'signed')
        self.assertEqual(self._get_xml_values(
            calls[0][1]['XMLContent'],
            'ExchangedDocument/TypeCode', 'NetLineTotalAmount', 'TaxBasisTotalAmount', 'TaxTotalAmount', 'GrandTotalAmount',
        ), [
            ['T03'],
            ['33.33', '33.33', '33.33'],
            ['99.99'],
            ['7.00', '2.34', '2.33', '2.33'],
            ['106.99'],
        ])

    def test_send_credit_note(self):
        invoice, tax_invoice = self._create_tax_invoice()
        credit_note = self._create_invoice(
            move_type='out_refund',
            partner_id=self.partner_a.id,
            reversed_entry_id=invoice.id,
            invoice_line_ids=[self._prepare_invoice_line(price_unit=100.0, tax_ids=self.tax_sale_a)],
            l10n_th_edi_credit_note_reason='CDNG04',
            post=True,
        )
        self.assertEqual(credit_note.l10n_th_edi_state, 'ready_to_send')

        with self._mock_inet(SIGNED) as calls:
            credit_note.action_l10n_th_edi_send()

        self.assertEqual(credit_note.l10n_th_edi_state, 'signed')
        self.assertEqual(self._get_xml_values(
            calls[0][1]['XMLContent'],
            'ExchangedDocument/TypeCode', 'PurposeCode', 'IssuerAssignedID', 'ReferenceTypeCode', 'OriginalInformationAmount',
            'LineTotalAmount', 'DifferenceInformationAmount', 'GrandTotalAmount',
        ), [['81'], ['CDNG04'], [tax_invoice.tax_invoice_number], ['388'], ['1000.00'], ['900.00'], ['100.00'], ['107.00']])

    def test_credit_note_reason_from_reversal_wizard(self):
        service = self._create_product(name="Consulting", type='service')
        invoice = self._create_invoice(
            partner_id=self.partner_a.id,
            invoice_line_ids=[self._prepare_invoice_line(product_id=service)],
            post=True,
        )

        wizard_form = Form(self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=invoice.ids))
        self.assertEqual(
            wizard_form.l10n_th_edi_available_reasons,
            ['CDNS01', 'CDNS02', 'CDNS03', 'CDNS04', 'CDNS99', 'DBNS01', 'DBNS02', 'DBNS99'],
        )
        wizard_form.l10n_th_edi_credit_note_reason = 'CDNS99'
        wizard_form.l10n_th_edi_other_reason = "Discount agreed after delivery"
        action = wizard_form.save().refund_moves()

        self.assertRecordValues(self.env['account.move'].browse(action['res_id']), [{
            'ref': f"Reversal of: {invoice.name}, Discount agreed after delivery",
            'l10n_th_edi_credit_note_reason': 'CDNS99',
            'l10n_th_edi_other_reason': "Discount agreed after delivery",
        }])

    def test_send_debit_note_from_debit_note_wizard(self):
        invoice, tax_invoice = self._create_tax_invoice()

        # As in l10n_it_edi, a line without a product is goods.
        wizard_form = Form(self.env['account.debit.note'].with_context(active_model='account.move', active_ids=invoice.ids))
        self.assertEqual(
            wizard_form.l10n_th_edi_available_reasons,
            ['CDNG01', 'CDNG02', 'CDNG03', 'CDNG04', 'CDNG05', 'CDNG99', 'DBNG01', 'DBNG02', 'DBNG99'],
        )
        wizard_form.l10n_th_edi_debit_note_reason = 'DBNG02'
        wizard_form.copy_lines = True
        debit_note = self.env['account.move'].browse(wizard_form.save().create_debit()['res_id'])
        self.assertRecordValues(debit_note, [{
            'ref': f"{invoice.name}, Miscalculated price of products lower than is the case",
            'l10n_th_edi_debit_note_reason': 'DBNG02',
        }])
        debit_note.action_post()
        # The debit note is sent as such, not through the tax invoice l10n_th creates for it.
        self.assertEqual(debit_note.l10n_th_edi_state, 'ready_to_send')
        self.assertFalse(debit_note.l10n_th_tax_invoice_ids.l10n_th_edi_state)

        with self._mock_inet(SIGNED) as calls:
            debit_note.action_l10n_th_edi_send()

        self.assertEqual(debit_note.l10n_th_edi_state, 'signed')
        self.assertEqual(self._get_xml_values(
            calls[0][1]['XMLContent'],
            'ExchangedDocument/TypeCode', 'PurposeCode', 'IssuerAssignedID', 'OriginalInformationAmount',
            'LineTotalAmount', 'DifferenceInformationAmount', 'GrandTotalAmount',
        ), [['80'], ['DBNG02'], [tax_invoice.tax_invoice_number], ['1000.00'], ['2000.00'], ['1000.00'], ['1070.00']])

    def test_checks_before_sending(self):
        _invoice, tax_invoice = self._create_tax_invoice()
        self.env.company.l10n_th_edi_subdistrict_code = '1017'
        self.partner_a.zip = False

        with self._mock_inet(), self.assertRaisesRegex(UserError, r'sub-district code(.|\n)*street, postcode and country'):
            tax_invoice.action_l10n_th_edi_send()

    def test_processing_document_is_not_signed_twice(self):
        _invoice, tax_invoice = self._create_tax_invoice()
        with self._mock_inet({'status': 'PC', 'transactionCode': 'TX1', 'errorCode': 'PC001', 'errorMessage': "Processing"}):
            tax_invoice.action_l10n_th_edi_send()
        self.assertRecordValues(tax_invoice, [{'l10n_th_edi_state': 'processing', 'l10n_th_edi_inet_transaction_code': 'TX1'}])

        # The status answer carries its own transaction code, not the document's.
        with self._mock_inet({**SIGNED, 'transactionCode': 'TX2'}) as calls:
            tax_invoice.action_l10n_th_edi_send()
        self.assertRecordValues(tax_invoice, [{'l10n_th_edi_state': 'signed', 'l10n_th_edi_inet_transaction_code': 'TX1'}])
        self.assertEqual(calls, [('/getdocument/getdocumentstatus', {
            'SellerTaxId': '0105561072420', 'SellerBranchId': '00000', 'SourceSystem': 'Odoo', 'TransactionCode': 'TX1',
        })])

    def test_lost_answer_is_checked_before_sending_again(self):
        _invoice, tax_invoice = self._create_tax_invoice()
        with self._mock_inet(requests.Timeout()):
            tax_invoice.action_l10n_th_edi_send()
        self.assertEqual(tax_invoice.l10n_th_edi_state, 'unknown')

        found = {'status': 'OK', 'totalRecord': 1, 'xmlURL': ['https://inet/xml'], 'pdfURL': ['https://inet/pdf']}
        signed_xml = tax_invoice._l10n_th_edi_get_xml(tax_invoice._l10n_th_edi_get_document_values())

        # Another system issued a document with the same number.
        with self._mock_inet(found, files={'https://inet/xml': signed_xml.replace(b'1070.00', b'2140.00')}):
            tax_invoice.action_l10n_th_edi_send()
        self.assertRecordValues(tax_invoice, [{
            'l10n_th_edi_state': 'error',
            'l10n_th_edi_error': f"INET holds another document numbered {tax_invoice.tax_invoice_number}.",
        }])
        tax_invoice.l10n_th_edi_state = 'unknown'

        # INET signed it after all.
        with self._mock_inet(found, files={'https://inet/xml': signed_xml}) as calls:
            tax_invoice.action_l10n_th_edi_send()
        self.assertEqual(tax_invoice.l10n_th_edi_state, 'signed')
        self.assertEqual(tax_invoice.l10n_th_edi_pdf_file_id.raw.content, b'signed https://inet/pdf')
        self.assertEqual([endpoint for endpoint, _fields in calls], ['/getdocument/getdocumentparams'])

    def test_duplicate_is_checked_before_saving_its_signed_files(self):
        _invoice, tax_invoice = self._create_tax_invoice()
        duplicate = {
            'status': 'ER', 'errorCode': 'ER011', 'errorMessage': "Duplicate document", 'transactionCode': 'TX2',
            'xmlURL': 'https://inet/xml', 'pdfURL': 'https://inet/pdf',
        }
        signed_xml = tax_invoice._l10n_th_edi_get_xml(tax_invoice._l10n_th_edi_get_document_values())

        with self._mock_inet(duplicate, files={'https://inet/xml': signed_xml.replace(b'1070.00', b'2140.00')}):
            tax_invoice.action_l10n_th_edi_send()
        self.assertRecordValues(tax_invoice, [{
            'l10n_th_edi_state': 'error',
            'l10n_th_edi_error': f"INET holds another document numbered {tax_invoice.tax_invoice_number}.",
        }])

        # A copy of this database sent it.
        with self._mock_inet(duplicate, files={'https://inet/xml': signed_xml}):
            tax_invoice.action_l10n_th_edi_send()
        self.assertRecordValues(tax_invoice, [{'l10n_th_edi_state': 'signed', 'l10n_th_edi_inet_transaction_code': False}])

    def test_rd_status_from_webhook_and_daily_check(self):
        _invoice, tax_invoice = self._create_tax_invoice()
        # The webhook and the daily check flush the signed PDF, which Documents reads if installed.
        with file_open('base/tests/files/file.pdf', 'rb') as pdf_file:
            pdf = pdf_file.read()
        with self._mock_inet(SIGNED, files={'https://inet/pdf': pdf}) as calls:
            tax_invoice.action_l10n_th_edi_send()
        callback_url = urlsplit(calls[0][1]['callbackUrl'])

        rd_status_url = callback_url.path.rpartition('/')[0]
        for wrong_token in (hash_sign(self.env, 'another_scope', [tax_invoice._name, tax_invoice.id]), 'garbage'):
            response = self.url_open(f'{rd_status_url}/{wrong_token}', json={'rdStatus': 'Submitted'})
            self.assertEqual(response.status_code, 404)

        response = self.url_open(callback_url.path, json={'rdStatus': 'Under RD review'})
        self.assertEqual(response.status_code, 204)
        self.env.invalidate_all()
        self.assertEqual(tax_invoice.l10n_th_edi_rd_state, 'in_review')

        # The webhook of the final status did not reach Odoo.
        cron = self.env.ref('l10n_th_edi_inet.ir_cron_l10n_th_edi_inet_update_rd_states_tax_invoice')
        with self._mock_inet({'status': 'ER', 'errorCode': 'ER500', 'errorMessage': "Service unavailable"}):
            cron.method_direct_trigger()
        self.assertRecordValues(tax_invoice, [{'l10n_th_edi_rd_state': 'in_review', 'l10n_th_edi_error': "[ER500] Service unavailable"}])

        with self._mock_inet({'status': 'OK', 'rdStatus': 'Failed', 'rdMessage': "Invalid buyer tax ID"}) as calls:
            cron.method_direct_trigger()
        self.assertRecordValues(tax_invoice, [{'l10n_th_edi_rd_state': 'failed', 'l10n_th_edi_error': "Invalid buyer tax ID"}])
        self.assertEqual(calls, [('/getdocument/getdocumentstatus', {
            'SellerTaxId': '0105561072420', 'SellerBranchId': '00000', 'SourceSystem': 'Odoo', 'TransactionCode': 'TX1',
        })])

        with self._mock_inet() as calls:
            cron.method_direct_trigger()
        self.assertFalse(calls)

    def test_lost_answer_of_unknown_document_is_sent_again(self):
        _invoice, tax_invoice = self._create_tax_invoice()
        with self._mock_inet(requests.ConnectionError()):
            tax_invoice.action_l10n_th_edi_send()

        with self._mock_inet({'status': 'ER', 'errorCode': 'ER019', 'errorMessage': "Not found", 'totalRecord': 0}, SIGNED) as calls:
            tax_invoice.action_l10n_th_edi_send()
        self.assertEqual(tax_invoice.l10n_th_edi_state, 'signed')
        self.assertEqual([endpoint for endpoint, _fields in calls], ['/getdocument/getdocumentparams', '/service/etaxsigndocument'])

    def test_rejected_document_can_be_sent_again(self):
        _invoice, tax_invoice = self._create_tax_invoice()
        with self._mock_inet({'status': 'ER', 'errorCode': 'FL004', 'errorMessage': "XML file failed for XSD check"}):
            tax_invoice.action_l10n_th_edi_send()
        self.assertRecordValues(tax_invoice, [{
            'l10n_th_edi_state': 'error',
            'l10n_th_edi_error': "[FL004] XML file failed for XSD check",
        }])

        with self._mock_inet(SIGNED):
            tax_invoice.action_l10n_th_edi_send()
        self.assertEqual(tax_invoice.l10n_th_edi_state, 'signed')
