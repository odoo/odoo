# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from freezegun import freeze_time

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from unittest.mock import patch

CALL_API_METHOD = 'odoo.addons.ecpay_invoice.utils.EcPayAPI.call_ecpay_api'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nTWITestEdi(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('tw')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'l10n_tw_edi_ecpay_api_url': 'https://einvoice-stage.ecpay.com.tw/B2CInvoice',
            'l10n_tw_edi_ecpay_merchant_id': '2000132',
            'l10n_tw_edi_ecpay_hashkey': 'ejCk326UnaZWKisg',
            'l10n_tw_edi_ecpay_hashIV': 'q9jcZX8Ib9LM8wYk',
            'l10n_tw_edi_ecpay_seller_identifier': '12345678',
            'phone': '+8860912345678',
        })
        cls.partner_a.write({
            'vat': '21313148',
            'phone': '+8860987654321',
            'contact_address': 'test address',
        })

        # We can reuse this invoice for the flow tests.
        cls.basic_invoice = cls.init_invoice(
            'out_invoice', partner=cls.partner_a, products=cls.product_a,
        )
        cls.basic_invoice.action_post()

        cls.fakenow = datetime(2024, 9, 22, 15, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_01_can_generate_file(self):
        """
        Simply test that with a valid configuration, we can generate the file.
        """
        json_data = self.basic_invoice._l10n_tw_edi_generate_invoice_json()
        self.assertTrue(json_data)

        # Validate the customer data
        self.assertEqual(json_data.get("MerchantID"), self.company_data['company'].l10n_tw_edi_ecpay_merchant_id)
        self.assertEqual(json_data.get("CustomerName"), self.basic_invoice.l10n_tw_edi_customer_name)
        self.assertEqual(json_data.get("CustomerAddr"), self.basic_invoice.l10n_tw_edi_customer_address)
        self.assertEqual(json_data.get("CustomerPhone"), self.basic_invoice.l10n_tw_edi_customer_phone)
        self.assertEqual(json_data.get("CustomerEmail"), self.basic_invoice.l10n_tw_edi_customer_email)
        self.assertEqual(json_data.get("SalesAmount"), self.basic_invoice.amount_total)

    def test_02_basic_submission(self):
        """
        This tests the most basic flow: an invoice is successfully sent to the MyInvois platform, and then pass validation.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_02_mock):
            send_and_print.action_send_and_print()
        # Now that the invoice has been sent successfully, we assert that some info have been saved correctly.
        self.assertRecordValues(
            self.basic_invoice,
            [{
                'l10n_tw_edi_ecpay_invoice_id': 'AB11100099',
                'l10n_tw_edi_invoice_create_date': datetime.strptime('2024-09-22 15:00:00', '%Y-%m-%d %H:%M:%S'),
                'l10n_tw_edi_state': 'valid',
                'l10n_tw_edi_invoice_amount': self.basic_invoice.amount_total,
                'l10n_tw_edi_invoice_valid_status': "0",
                'l10n_tw_edi_invoice_issue_status': "1",
                'l10n_tw_edi_invoice_shop_custom_number': "20241028000000020",
                'l10n_tw_edi_remain_refundable_amount': 0,
            }]
        )

        # We will test the actual file in another test class, but we ensure it was generated as expected.
        self.assertTrue(self.basic_invoice.l10n_tw_edi_file_id)

    def test_03_failed_submission(self):
        """
        This test will test a flow where the submission itself (not the documents inside) fails for any reason.
        A general error as such should be handled, but is not expected and should be treated as a bug on our side.

        As we submit a single invoice, we expect a UserError to be raised.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_03_mock):
            with self.assertRaises(UserError):
                send_and_print.action_send_and_print()

    def test_04_invalid_invoice(self):
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_04_mock):
            send_and_print.action_send_and_print()
            wizard_vals = {'journal_id': self.basic_invoice.journal_id.id}
            wizard_reverse = self.env['account.move.reversal'].with_context(active_ids=self.basic_invoice.id, active_model='account.move').create(wizard_vals)
            wizard_reverse.reverse_moves(is_modify=True)

        self.assertRecordValues(
            self.basic_invoice,
            [{
                'l10n_tw_edi_state': 'invalid',
            }]
        )

    def test_05_refund_invoice(self):
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_05_mock):
            send_and_print.action_send_and_print()
            wizard_vals = {'journal_id': self.basic_invoice.journal_id.id}
            wizard_reverse = self.env['account.move.reversal'].with_context(active_ids=self.basic_invoice.id, active_model='account.move').create(wizard_vals)
            wizard_reverse.reverse_moves(is_modify=False)
            credit_note = wizard_reverse.new_move_ids
            credit_note.l10n_tw_edi_run_refund()
        self.assertEqual(credit_note.l10n_tw_edi_refund_agreement_type, wizard_reverse.l10n_tw_edi_refund_agreement_type)
        self.assertEqual(credit_note.l10n_tw_edi_origin_invoice_number, self.basic_invoice)
        self.assertEqual(credit_note.l10n_tw_edi_ecpay_invoice_id, self.basic_invoice.l10n_tw_edi_ecpay_invoice_id)
        self.assertEqual(credit_note.l10n_tw_edi_invoice_create_date, self.basic_invoice.l10n_tw_edi_invoice_create_date)
        self.assertTrue(credit_note.l10n_tw_edi_is_refund)
        self.assertRecordValues(
            credit_note,
            [{
                'l10n_tw_edi_refund_invoice_number': '20241028000000021',
                'l10n_tw_edi_refund_finish': True,
                'l10n_tw_edi_refund_state': 'agreed',
            }]
        )
        self.assertRecordValues(
            self.basic_invoice,
            [{
                'l10n_tw_edi_remain_refundable_amount': 0,
            }]
        )

    # -------------------------------------------------------------------------
    # Patched methods
    # -------------------------------------------------------------------------

    def _test_02_mock(self, endpoint, params):
        if endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/Issue'):
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2024-09-22 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/GetIssue'):
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.basic_invoice.amount_total,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20241028000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_03_mock(self, endpoint, params):
        if endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/Issue'):
            return {
                "RtnCode": 0,
                "RtnMsg": "Error",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_04_mock(self, endpoint, params):
        if endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/Issue'):
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2024-09-22 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/GetIssue'):
            return_data = {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.basic_invoice.amount_total,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20241028000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
            return return_data
        elif endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/Invalid'):
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099"
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_05_mock(self, endpoint, params):
        if endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/Issue'):
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2024-09-22 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/GetIssue'):
            return_data = {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.basic_invoice.amount_total,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20241028000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
            return return_data
        elif endpoint == (self.company_data['company'].l10n_tw_edi_ecpay_api_url + '/Allowance'):
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IA_Allow_No": "20241028000000021",
                "IA_Invoice_No": "AB11100099",
                "IA_Date": "2024-09-22 23:00:00",
                "IA_Remain_Allowance_Amt": 0,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))
