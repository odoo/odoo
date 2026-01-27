# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from unittest import mock
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestVNEDI(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('vn')
    def setUpClass(cls):
        super().setUpClass()

        # Setup the default symbol and template.
        cls.template = cls.env['l10n_vn_edi_viettel.sinvoice.template'].create({
            'name': '1/001',
            'template_invoice_type': '1',
        })
        cls.symbol = cls.env['l10n_vn_edi_viettel.sinvoice.symbol'].create({
            'name': 'K24TUT',
            'invoice_template_id': cls.template.id,
        })
        cls.env['ir.default'].set(
            'res.partner',
            'l10n_vn_edi_symbol',
            cls.symbol.id,
            company_id=cls.env.company.id
        )

        # Setup a vietnamese address on the partner and company.
        cls.partner_a.write({
            'street': '121 Hang Bac Street',
            'state_id': cls.env.ref('base.state_vn_VN-HN').id,
            'city': 'Hà Nội',
            'country_id': cls.env.ref('base.vn').id,
            'vat': '0100109106-505',
            'phone': '3825 7670',
            'email': 'partner_a@gmail.com',
        })

        cls.env.company.write({
            'street': '3 Alley 45 Phan Dinh Phung, Quan Thanh Ward',
            'state_id': cls.env.ref('base.state_vn_VN-HN').id,
            'country_id': cls.env.ref('base.vn').id,
            'vat': '0100109106-506',
            'phone': '6266 1275',
            'email': 'test_company@gmail.com',
            'website': 'test_company.com',
            'l10n_vn_edi_password': 'a',
            'l10n_vn_edi_username': 'b',
        })

        cls.product_a.default_code = 'BN/1035'
        cls.other_currency = cls.setup_other_currency('EUR')

    @freeze_time('2024-01-01')
    def test_invoice_creation(self):
        """ Create an invoice, and post it. Ensure that the status and symbol is set correctly during this flow. """
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
        )
        self.assertFalse(invoice.l10n_vn_edi_invoice_state)  # State should be False before posting.
        self.assertEqual(invoice.l10n_vn_edi_invoice_symbol.id, self.symbol.id)
        invoice.action_post()
        self.assertEqual(invoice.l10n_vn_edi_invoice_state, 'ready_to_send')

    @freeze_time('2024-01-01')
    def test_default_symbol_on_partner(self):
        """ Ensure that the default symbol is set correctly if set on the partner of the invoice. """
        self.partner_a.l10n_vn_edi_symbol = self.env['l10n_vn_edi_viettel.sinvoice.symbol'].create({
            'name': 'K24TUD',
            'invoice_template_id': self.template.id,
        })
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
        )
        self.assertEqual(invoice.l10n_vn_edi_invoice_symbol.id, self.partner_a.l10n_vn_edi_symbol.id)

    @freeze_time('2024-01-01')
    def test_json_data_generation(self):
        """ Test the data dict generated to ensure consistency with the data we set in the system. """
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
            taxes=self.tax_sale_a,
            post=True,
        )
        self.assertDictEqual(
            invoice._l10n_vn_edi_generate_invoice_json(),
            {
                'generalInvoiceInfo': {
                    'transactionUuid': mock.ANY,  # Random, not important.
                    'invoiceType': '1',
                    'templateCode': '1/001',
                    'invoiceSeries': 'K24TUT',
                    'invoiceIssuedDate': 1704067200000,
                    'currencyCode': 'VND',
                    'adjustmentType': '1',
                    'paymentStatus': False,
                    'cusGetInvoiceRight': True,
                    'validation': 1,
                },
                'buyerInfo': {
                    'buyerName': 'partner_a',
                    'buyerLegalName': 'partner_a',
                    'buyerTaxCode': '0100109106-505',
                    'buyerAddressLine': '121 Hang Bac Street',
                    'buyerPhoneNumber': '38257670',
                    'buyerEmail': 'partner_a@gmail.com',
                    'buyerCityName': 'Hà Nội',
                    'buyerCountryCode': 'VN',
                    'buyerNotGetInvoice': 0,
                },
                'sellerInfo': {
                    'sellerLegalName': 'company_1_data',
                    'sellerTaxCode': '0100109106-506',
                    'sellerAddressLine': '3 Alley 45 Phan Dinh Phung, Quan Thanh Ward',
                    'sellerPhoneNumber': '62661275',
                    'sellerEmail': 'test_company@gmail.com',
                    'sellerDistrictName': 'Hà Nội',
                    'sellerCountryCode': 'VN',
                    'sellerWebsite': 'http://test_company.com',
                },
                'payments': [{'paymentMethodName': 'TM/CK'}],
                'itemInfo': [{
                    'itemCode': 'BN/1035',
                    'itemName': '[BN/1035] product_a',
                    'unitName': 'Units',
                    'unitPrice': 1000.0,
                    'quantity': 1.0,
                    'itemTotalAmountWithoutTax': 1000.0,
                    'taxPercentage': 10.0,
                    'taxAmount': 100.0,
                    'discount': 0.0,
                    'itemTotalAmountAfterDiscount': 1000.0,
                    'itemTotalAmountWithTax': 1100.0,
                    'selection': 1,
                }],
                'taxBreakdowns': [{
                    'taxPercentage': 10.0,
                    'taxableAmount': 1000.0,
                    'taxAmount': 100.0,
                    'taxableAmountPos': True,
                    'taxAmountPos': True
                }]
            }
        )

    @freeze_time('2024-01-01')
    def test_json_data_generation_no_product(self):
        """ Test the data dict generated to ensure consistency with the data we set in the system. """
        invoice = self.init_invoice(
            move_type='out_invoice',
            amounts=[250],
            taxes=self.tax_sale_a,
            post=True,
        )
        self.assertDictEqual(
            invoice._l10n_vn_edi_generate_invoice_json(),
            {
                'generalInvoiceInfo': {
                    'transactionUuid': mock.ANY,  # Random, not important.
                    'invoiceType': '1',
                    'templateCode': '1/001',
                    'invoiceSeries': 'K24TUT',
                    'invoiceIssuedDate': 1704067200000,
                    'currencyCode': 'VND',
                    'adjustmentType': '1',
                    'paymentStatus': False,
                    'cusGetInvoiceRight': True,
                    'validation': 1,
                },
                'buyerInfo': {
                    'buyerName': 'partner_a',
                    'buyerLegalName': 'partner_a',
                    'buyerTaxCode': '0100109106-505',
                    'buyerAddressLine': '121 Hang Bac Street',
                    'buyerPhoneNumber': '38257670',
                    'buyerEmail': 'partner_a@gmail.com',
                    'buyerCityName': 'Hà Nội',
                    'buyerCountryCode': 'VN',
                    'buyerNotGetInvoice': 0,
                },
                'sellerInfo': {
                    'sellerLegalName': 'company_1_data',
                    'sellerTaxCode': '0100109106-506',
                    'sellerAddressLine': '3 Alley 45 Phan Dinh Phung, Quan Thanh Ward',
                    'sellerPhoneNumber': '62661275',
                    'sellerEmail': 'test_company@gmail.com',
                    'sellerDistrictName': 'Hà Nội',
                    'sellerCountryCode': 'VN',
                    'sellerWebsite': 'http://test_company.com',
                },
                'payments': [{'paymentMethodName': 'TM/CK'}],
                'itemInfo': [{
                    'itemCode': '',
                    'itemName': 'test line',
                    'unitName': 'Units',
                    'unitPrice': 250.0,
                    'quantity': 1.0,
                    'itemTotalAmountWithoutTax': 250.0,
                    'taxPercentage': 10.0,
                    'taxAmount': 25.0,
                    'discount': 0.0,
                    'itemTotalAmountAfterDiscount': 250.0,
                    'itemTotalAmountWithTax': 275.0,
                    'selection': 1,
                }],
                'taxBreakdowns': [{
                    'taxPercentage': 10.0,
                    'taxableAmount': 250.0,
                    'taxAmount': 25.0,
                    'taxableAmountPos': True,
                    'taxAmountPos': True
                }]
            }
        )

    @freeze_time('2024-01-01')
    def test_adjustment_invoice(self):
        """
        Create an invoice, then create an adjustment invoice from it. Ensure that when generating the data dict,
        the related fields are set correctly.
        """
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
            taxes=self.tax_sale_a,
            post=True,
        )
        invoice.write({  # Would be set by sending it to the edi
            'l10n_vn_edi_invoice_number': 'K24TUT01',
            'l10n_vn_edi_issue_date': fields.Datetime.now(),
            'l10n_vn_edi_invoice_state': 'sent',
        })
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'reason': 'Correcting price',
            'journal_id': invoice.journal_id.id,
            'l10n_vn_edi_adjustment_type': '1',
            'l10n_vn_edi_agreement_document_name': 'N/A',
            'l10n_vn_edi_agreement_document_date': fields.Datetime.now(),
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        reverse_move.invoice_line_ids[0].price_unit = 100  # We invoiced 100 too much
        json_data = reverse_move._l10n_vn_edi_generate_invoice_json()
        # 1. Check the general info values, ensure correct adjustment type, and that the data were correctly fetched from the original invoice.
        expected = {
            'adjustmentType': '5',
            'adjustmentInvoiceType': '1',
            'originalInvoiceId': 'K24TUT01',
            'originalInvoiceIssueDate': 1704067200000,
            'originalTemplateCode': '1/001',
            'additionalReferenceDesc': 'N/A',
            'additionalReferenceDate': 1704067200000,
        }
        actual = json_data['generalInvoiceInfo']
        self.assertDictEqual(actual, actual | expected)
        # 2. Check the itemInfo to ensure that the values make sense
        expected = {
            'unitPrice': -100.0,
            'itemTotalAmountWithoutTax': 100.0,
            'taxAmount': 10.0,
            'itemTotalAmountWithTax': 110.0,
            'adjustmentTaxAmount': 10.0,
            'isIncreaseItem': False,
        }
        actual = json_data['itemInfo'][0]
        self.assertDictEqual(actual, actual | expected)

    @freeze_time('2024-01-01')
    def test_replacement_invoice(self):
        """
        Create an invoice, then create a replacement invoice from it. Ensure that when generating the data dict,
        the related fields are set correctly.
        """
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
            taxes=self.tax_sale_a,
            post=True,
        )
        invoice.write({  # Would be set by sending it to the edi
            'l10n_vn_edi_invoice_number': 'K24TUT01',
            'l10n_vn_edi_issue_date': fields.Datetime.now(),
            'l10n_vn_edi_invoice_state': 'sent',
        })
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'reason': 'Correcting price',
            'journal_id': invoice.journal_id.id,
            'l10n_vn_edi_adjustment_type': '1',
            'l10n_vn_edi_agreement_document_name': 'N/A',
            'l10n_vn_edi_agreement_document_date': fields.Datetime.now(),
        })
        reversal = move_reversal.reverse_moves(is_modify=True)
        reverse_move = self.env['account.move'].browse(reversal['res_id'])
        reverse_move.invoice_line_ids[0].price_unit = 900  # New price is 900 and not 1000
        json_data = reverse_move._l10n_vn_edi_generate_invoice_json()
        # 1. Check the general info values, ensure correct adjustment type, and that the data were correctly fetched from the original invoice.
        expected = {
            'adjustmentType': '3',
            'adjustmentInvoiceType': '1',
            'originalInvoiceId': 'K24TUT01',
            'originalInvoiceIssueDate': 1704067200000,
            'originalTemplateCode': '1/001',
            'additionalReferenceDesc': 'N/A',
            'additionalReferenceDate': 1704067200000,
        }
        actual = reverse_move._l10n_vn_edi_generate_invoice_json()['generalInvoiceInfo']
        self.assertDictEqual(actual, actual | expected)
        # 2. Check the itemInfo to ensure that the values make sense
        expected = {
            'unitPrice': 900.0,
            'itemTotalAmountWithoutTax': 900.0,
            'taxAmount': 90.0,
            'itemTotalAmountWithTax': 990.0,
        }
        actual = json_data['itemInfo'][0]
        self.assertDictEqual(actual, actual | expected)

    @freeze_time('2024-01-01')
    def test_invoice_foreign_currency(self):
        """ When invoicing in a foreign currency, we are required to include the rate at the time of the invoice. """
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
            taxes=self.tax_sale_a,
            post=True,
            currency=self.other_currency,
        )
        json_data = invoice._l10n_vn_edi_generate_invoice_json()
        self.assertEqual(json_data['generalInvoiceInfo']['exchangeRate'], "0.50")

    @freeze_time('2024-01-01')
    def test_send_and_print(self):
        """ Test the send & print settings and flows.

        Note: we are not trying to test the API, thus the few api call will be mocked to not happen.
        """
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
            taxes=self.tax_sale_a,
            post=True,
            currency=self.other_currency,
        )
        self.assertEqual(invoice.l10n_vn_edi_invoice_state, 'ready_to_send')
        self._send_invoice(invoice)

        # Check a few things that should be set by the send & print: invoice number, attachments, state, reservation code.
        self.assertRecordValues(
            invoice,
            [{
                'l10n_vn_edi_invoice_number': 'K24TUT01',
                'l10n_vn_edi_reservation_code': '123456',
                'l10n_vn_edi_invoice_state': 'sent',
            }]
        )
        self.assertNotEqual(invoice.l10n_vn_edi_sinvoice_xml_file, False)
        self.assertNotEqual(invoice.l10n_vn_edi_sinvoice_pdf_file, False)
        self.assertNotEqual(invoice.l10n_vn_edi_sinvoice_file, False)

    @freeze_time('2024-01-01')
    def test_cancel_invoice(self):
        """ Ensure that trying to cancel a sent invoice returns the wizard action, and test the wizard flow. """
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
            taxes=self.tax_sale_a,
            post=True,
            currency=self.other_currency,
        )
        self._send_invoice(invoice)
        # Trying to cancel a sent invoice should result in an action to open the cancellation wizard.
        action = invoice.button_request_cancel()
        self.assertEqual(action['res_model'], 'l10n_vn_edi_viettel.cancellation')
        with patch('odoo.addons.l10n_vn_edi_viettel.models.account_move._l10n_vn_edi_send_request', return_value=(None, None)):
            self.env['l10n_vn_edi_viettel.cancellation'].create({
                'invoice_id': invoice.id,
                'reason': 'Unwanted',
                'agreement_document_name': 'N/A',
                'agreement_document_date': fields.Datetime.now(),
            }).button_request_cancel()
        # Both states should be canceled, but the e-invoicing data should still be there
        self.assertEqual(invoice.l10n_vn_edi_invoice_state, 'canceled')
        self.assertEqual(invoice.state, 'cancel')
        self.assertNotEqual(invoice.l10n_vn_edi_invoice_number, False)

    def test_access_token(self):
        """ Ensure that we can fetch access tokens as you would expect. """
        invoice = self.init_invoice(
            move_type='out_invoice',
            products=self.product_a,
            taxes=self.tax_sale_a,
            post=True,
            currency=self.other_currency,
        )
        request_response = {
            'access_token': '123',  # In reality, it wouldn't be set here, but for convenience in the tests we'll "cheat"
            'expires_in': '600',  # 10m
        }

        # Do a few tests to ensure that the access token is handled correctly.
        with patch('odoo.addons.l10n_vn_edi_viettel.models.account_move._l10n_vn_edi_send_request', return_value=(request_response, None)):
            # First ensure that fetching the token will set the value correctly on the company.
            with freeze_time('2024-01-01 02:00:00'):
                invoice._l10n_vn_edi_get_access_token()
                self.assertEqual(invoice.company_id.l10n_vn_edi_token, '123')
                self.assertEqual(invoice.company_id.l10n_vn_edi_token_expiry, datetime.strptime('2024-01-01 02:10:00', '%Y-%m-%d %H:%M:%S'))
            # Second fetch should not set anything as the token isn't expired.
            with freeze_time('2024-01-01 02:05:00'):
                invoice._l10n_vn_edi_get_access_token()
                self.assertEqual(invoice.company_id.l10n_vn_edi_token, '123')
                self.assertEqual(invoice.company_id.l10n_vn_edi_token_expiry, datetime.strptime('2024-01-01 02:10:00', '%Y-%m-%d %H:%M:%S'))
            # Third fetch will get a new token due as it expired
            with freeze_time('2024-01-01 02:15:00'):
                invoice._l10n_vn_edi_get_access_token()
                self.assertEqual(invoice.company_id.l10n_vn_edi_token, '123')
                self.assertEqual(invoice.company_id.l10n_vn_edi_token_expiry, datetime.strptime('2024-01-01 02:25:00', '%Y-%m-%d %H:%M:%S'))

    def _send_invoice(self, invoice):
        pdf_response = {
            'name': 'sinvoice.pdf',
            'mimetype': 'application/pdf',
            'raw': b'pdf file',
            'res_field': 'l10n_vn_edi_sinvoice_pdf_file',
        }, ""
        xml_response = {
            'name': 'sinvoice.xml',
            'mimetype': 'application/xml',
            'raw': b'xml file',
            'res_field': 'l10n_vn_edi_sinvoice_xml_file',
        }, ""
        request_response = {
            'result': {
                'reservationCode': '123456',
                'invoiceNo': 'K24TUT01',
            },
            'access_token': '123',  # In reality, it wouldn't be set here, but for convenience in the tests we'll "cheat"
            'expires_in': '60',
        }

        with patch('odoo.addons.l10n_vn_edi_viettel.models.account_move.AccountMove._l10n_vn_edi_fetch_invoice_pdf_file_data', return_value=pdf_response), \
             patch('odoo.addons.l10n_vn_edi_viettel.models.account_move.AccountMove._l10n_vn_edi_fetch_invoice_xml_file_data', return_value=xml_response), \
             patch('odoo.addons.l10n_vn_edi_viettel.models.account_move._l10n_vn_edi_send_request', return_value=(request_response, None)):
            self.env['account.move.send.wizard'].with_context(active_model=invoice._name, active_ids=invoice.ids).create({}).action_send_and_print()

    @freeze_time('2024-01-01')
    def test_decimal_rounding(self):
        """ Test that taxAmount are correctly rounded in the JSON data. """
        invoice = self.init_invoice(
            move_type='out_invoice',
            amounts=[1000.25],
            taxes=self.tax_sale_a,
            currency=self.other_currency,
            post=True,
        )
        json_values = invoice._l10n_vn_edi_generate_invoice_json()
        itemInfo = json_values['itemInfo'][0]
        self.assertEqual(itemInfo['taxAmount'], 100.03, "Tax amount should be correctly rounded to 2 decimals.")
