# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch
from urllib.parse import urljoin

from freezegun import freeze_time

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import HttpCase

CALL_API_METHOD = 'odoo.addons.l10n_tw_edi_ecpay.models.account_move.call_ecpay_api'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nTWITestEdi(TestAccountMoveSendCommon, HttpCase):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('tw')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'l10n_tw_edi_ecpay_staging_mode': True,
            'l10n_tw_edi_ecpay_merchant_id': '1234',
            'l10n_tw_edi_ecpay_hashkey': 'aaBBccDDeeFFggHH',
            'l10n_tw_edi_ecpay_hashIV': 'bbCCDDeeFFggHHaa',
            'phone': '+886 123 456 781',
        })
        cls.partner_a.write({
            'phone': '+886 123 456 789',
            'contact_address': 'test address',
            'company_type': 'person',
        })

        # We can reuse this invoice for the flow tests.
        cls.basic_invoice = cls.init_invoice(
            'out_invoice', partner=cls.partner_a, products=cls.product_a,
        )
        cls.basic_invoice.action_post()

    def test_01_can_generate_file(self):
        """
        Simply test that with a valid configuration, we can generate the file.
        """
        with patch(CALL_API_METHOD, new=self._test_01_mock):
            json_data = self.basic_invoice._l10n_tw_edi_generate_invoice_json()
        self.assertTrue(json_data)

        # Validate the customer data
        self.assertEqual(json_data.get("MerchantID"), "1234")
        self.assertEqual(json_data.get("CustomerName"), "partner_a")
        self.assertEqual(json_data.get("CustomerEmail"), "partner_a@tsointsoin")
        self.assertEqual(json_data.get("CustomerPhone"), "0123456789")
        self.assertEqual(json_data.get("SalesAmount"), 1050.0)

    @freeze_time("2025-01-06 15:00:00")
    def test_02_basic_submission(self):
        """
        This tests the most basic flow: an invoice is successfully sent to the ECpay platform, and then pass validation.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_02_mock):
            send_and_print.action_send_and_print()

        # Now that the invoice has been sent successfully, we assert that some info have been saved correctly.
        self.assertRecordValues(
            self.basic_invoice,
            [{
                'l10n_tw_edi_ecpay_invoice_id': 'AB11100099',
                'l10n_tw_edi_invoice_create_date': datetime.strptime('2025-01-06 15:00:00', '%Y-%m-%d %H:%M:%S'),
                'l10n_tw_edi_state': 'valid',
            }]
        )

        self.assertTrue(self.basic_invoice.l10n_tw_edi_file_id)

    def test_03_failed_submission(self):
        """
        This test will test a flow that fails when sending the invoice to the ECpay platform, an UserError to be raised
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_03_mock):
            with self.assertRaises(UserError):
                send_and_print.action_send_and_print()

    @freeze_time("2025-01-06 15:00:00")
    def test_04_invalid_invoice(self):
        """
        This tests the flow of invalidating an invoice that has already been sent to the ECpay platform.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_04_mock):
            send_and_print.action_send_and_print()
            wizard_vals = {'journal_id': self.basic_invoice.journal_id.id, 'reason': 'refund'}
            wizard_reverse = self.env['account.move.reversal']\
                .with_context(active_ids=self.basic_invoice.id, active_model='account.move').create(wizard_vals)
            wizard_reverse.reverse_moves(is_modify=True)
        self.assertEqual(self.basic_invoice.l10n_tw_edi_state, 'invalid')

    @freeze_time("2025-01-06 15:00:00")
    def test_05_refund_invoice(self):
        """
        This tests the flow of refunding an invoice that has already been sent to the ECpay platform with an offline
        agreement type.
        And make sure that the credit note is created with the correct fields and values from the wizard
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_05_mock):
            send_and_print.action_send_and_print()
            wizard_vals = {
                'journal_id': self.basic_invoice.journal_id.id,
                'l10n_tw_edi_refund_agreement_type': 'offline',
                'l10n_tw_edi_allowance_notify_way': 'email',
                'reason': 'refund',
            }
            wizard_reverse = self.env['account.move.reversal']\
                .with_context(active_ids=self.basic_invoice.id, active_model='account.move').create(wizard_vals)
            wizard_reverse.reverse_moves(is_modify=False)
            credit_note = wizard_reverse.new_move_ids
            credit_note.action_post()
            send_and_print_credit_note = self.create_send_and_print(credit_note)
            send_and_print_credit_note.action_send_and_print()
        self.assertRecordValues(
            credit_note,
            [{
                'reversed_entry_id': self.basic_invoice.id,
                'l10n_tw_edi_refund_agreement_type': 'offline',
                'l10n_tw_edi_refund_invoice_number': '20250106000000021',
                'l10n_tw_edi_refund_state': 'agreed',
                'l10n_tw_edi_ecpay_invoice_id': 'AB11100099',
                'l10n_tw_edi_invoice_create_date': datetime(2025, 1, 6, 15, 0, 0),
            }]
        )

    @freeze_time("2025-01-06 15:00:00")
    def test_06_refund_invoice_agreed_invoice_allowance(self):
        """
        This tests the flow of refunding an invoice that has already been sent to the ECpay platform with an online
        agreement type including the flow that customer agreeing to the invoice allowance.
        And make sure that the credit note is created with the correct fields and values from the wizard
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CALL_API_METHOD, new=self._test_06_mock):
            send_and_print.action_send_and_print()
            wizard_vals = {
                'journal_id': self.basic_invoice.journal_id.id,
                'l10n_tw_edi_refund_agreement_type': 'online',
                'l10n_tw_edi_allowance_notify_way': 'email',
                'reason': 'refund',
            }
            wizard_reverse = self.env['account.move.reversal']\
                .with_context(active_ids=self.basic_invoice.id, active_model='account.move').create(wizard_vals)
            wizard_reverse.reverse_moves(is_modify=False)
            credit_note = wizard_reverse.new_move_ids
            credit_note.action_post()
            send_and_print_credit_note = self.create_send_and_print(credit_note)
            send_and_print_credit_note.action_send_and_print()
        self.assertRecordValues(
            credit_note,
            [{
                'reversed_entry_id': self.basic_invoice.id,
                'l10n_tw_edi_refund_agreement_type': 'online',
                'l10n_tw_edi_refund_invoice_number': '20250106000000021',
                'l10n_tw_edi_refund_state': 'to_be_agreed',
                'l10n_tw_edi_ecpay_invoice_id': 'AB11100099',
                'l10n_tw_edi_invoice_create_date': datetime(2025, 1, 6, 15, 0, 0),
            }]
        )

        # test the step that the customer agrees invoice allowance
        api_url = urljoin(
            credit_note.get_base_url(),
            f"/invoice/ecpay/agreed_invoice_allowance/{credit_note.id}?access_token={credit_note._portal_ensure_token()}")
        response = self.url_open(
            api_url,
            data={"RtnCode": "1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertRecordValues(
            credit_note,
            [{
                'l10n_tw_edi_refund_invoice_number': '20250106000000021',
                'l10n_tw_edi_refund_state': 'agreed',
            }]
        )

    def test_07_fail_data_validation(self):
        """
        This tests the data validation when trying to send to the ECpay platform.
        """
        # the partner is b2b but has no tax id
        test_partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'phone': '+886 123 456 789',
            'contact_address': 'test address',
            'company_type': 'company',
        })
        invoice_a = self.init_invoice(
            'out_invoice', partner=test_partner, products=self.product_a,
        )
        invoice_a.action_post()
        send_and_print = self.create_send_and_print(invoice_a)
        with self.assertRaises(UserError):
            send_and_print.action_send_and_print()

        # the partner is b2b and has an invalid tax id
        test_partner.vat = '1234567A'
        invoice_b = self.init_invoice(
            'out_invoice', partner=test_partner, products=self.product_a,
        )
        invoice_b.action_post()
        send_and_print = self.create_send_and_print(invoice_b)
        with self.assertRaises(UserError):
            send_and_print.action_send_and_print()

        # the partner's phone number is invalid
        test_partner.vat = '12345678'
        test_partner.phone = '123+456+789'
        invoice_c = self.init_invoice(
            'out_invoice', partner=test_partner, products=self.product_a,
        )
        invoice_c.action_post()
        send_and_print = self.create_send_and_print(invoice_c)
        with self.assertRaises(UserError):
            send_and_print.action_send_and_print()
        # the invoice type is invalid
        test_partner.phone = '+886 123 456 789'
        invoice_d = self.init_invoice(
            'out_invoice', partner=test_partner, products=self.product_a,
        )
        invoice_d.l10n_tw_edi_invoice_type = '08'
        invoice_d.action_post()
        send_and_print = self.create_send_and_print(invoice_d)
        with self.assertRaises(UserError):
            send_and_print.action_send_and_print()

    # -------------------------------------------------------------------------
    # Patched methods
    # -------------------------------------------------------------------------
    def _test_01_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 1,
                "CompanyName": "Test Company",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_02_mock(self, endpoint, json_data, company_id, is_b2b=False):
        if endpoint == "/Issue":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2025-01-06 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == "/GetIssue":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.basic_invoice.amount_total,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20250106000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
        elif endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 1,
                "CompanyName": "Test Company",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, json_data))

    def _test_03_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/Issue":
            return {
                "RtnCode": 0,
                "RtnMsg": "Error",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_04_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/Issue":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2025-01-06 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == "/GetIssue":
            return_data = {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.basic_invoice.amount_total,
                "IIS_Invalid_Status": "1" if self.basic_invoice.l10n_tw_edi_invalidate_reason else "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20250106000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
            return return_data
        elif endpoint == "/Invalid":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099"
            }
        elif endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 1,
                "CompanyName": "Test Company",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_05_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/Issue":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2025-01-06 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == "/GetIssue":
            return_data = {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.basic_invoice.amount_total,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20250106000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
            return return_data
        elif endpoint == "/Allowance":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IA_Allow_No": "20250106000000021",
                "IA_Invoice_No": "AB11100099",
                "IA_Date": "2025-01-06 23:00:00",
                "IA_Remain_Allowance_Amt": 0,
            }
        elif endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 1,
                "CompanyName": "Test Company",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_06_mock(self, endpoint, params, company_id, is_b2b=False):
        if endpoint == "/Issue":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "InvoiceNo": "AB11100099",
                "InvoiceDate": "2025-01-06 23:00:00",
                "RandomNumber": "6868"
            }
        elif endpoint == "/GetIssue":
            return_data = {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IIS_Sales_Amount": self.basic_invoice.amount_total,
                "IIS_Invalid_Status": "0",
                "IIS_Issue_Status": "1",
                "IIS_Relate_Number": "20250106000000020",
                "IIS_Remain_Allowance_Amt": 0,
            }
            return return_data
        elif endpoint == "/AllowanceByCollegiate":
            return {
                "RtnCode": 1,
                "RtnMsg": "Success",
                "IA_Allow_No": "20250106000000021",
                "IA_Invoice_No": "AB11100099",
                "IA_Date": "2025-01-06 23:00:00",
                "IA_Remain_Allowance_Amt": 0,
            }
        elif endpoint == "/GetCompanyNameByTaxID":
            return {
                "RtnCode": 1,
                "CompanyName": "Test Company",
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))
