# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import urljoin

from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import HttpCase

IAP_PROXY_METHOD = "odoo.addons.l10n_id_pajakio.models.iap_account.IapAccount._l10n_id_pajakio_iap_connect"

@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nIdPajakio(TestAccountMoveSendCommon, HttpCase):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('id')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            "city": "Jakarta",
            "vat": "1234567890123456"
        })
        cls.partner_a.write({
            "city": "Jakarta",
            'country_id': cls.env.ref('base.id').id,
            'company_type': 'person',
            'l10n_id_pkp': True,
            "vat": "1234567890123456",
        })
        cls.basic_invoice = cls.init_invoice(
            'out_invoice', partner=cls.partner_a, products=cls.product_a, taxes=cls.tax_sale_a,
        )
        cls.basic_invoice.action_post()
        cls.env['ir.config_parameter'].set_param('l10n_id_pajakio.active', True)

    def test_error_file_generation(self):
        """ Test that there are conditions in which the file cannot be generated.

        Conditions include:
        - VAT and city is not configured yet on the company configuration
        - Customers:
            - are not tax-eligible (l10n_id_pkp is False)
            - do not have their VAT configured yet
            - do not have their city configured yet
        - Invoices:
            - are not posted yet
            - do not contain any taxes
        """
        # Case 1: VAT and city is not configured on the company
        self.company_data['company'].write({
            "city": False,
            "vat": False,
        })
        with self.assertRaises(UserError, msg="Company without city and VAT should not be able to generate pajak.io file"):
            self.basic_invoice._prepare_invoice_payload_pajakio()

        # Case 2: Customer is not tax-eligible
        self.partner_a.l10n_id_pkp = False
        with self.assertRaises(UserError, msg="Customer that is not tax-eligible should not be able to generate pajak.io file"):
            self.basic_invoice._prepare_invoice_payload_pajakio()
        self.partner_a.l10n_id_pkp = True

        # Case 3: Customer does not have VAT configured
        self.partner_a.vat = False
        with self.assertRaises(UserError, msg="Customer without VAT should not be able to generate pajak.io file"):
            self.basic_invoice._prepare_invoice_payload_pajakio()
        self.partner_a.vat = "1234567890123456"

        # Case 4: Customer does not have city configured
        self.partner_a.city = False
        with self.assertRaises(UserError, msg="Customer without city should not be able to generate pajak.io file"):
            self.basic_invoice._prepare_invoice_payload_pajakio()
        self.partner_a.city = "Jakarta"

        # Case 5: Invoice is not posted yet
        draft_invoice = self.init_invoice('out_invoice', partner=self.partner_a, products=self.product_a, taxes=self.tax_sale_a)
        with self.assertRaises(UserError, msg="Invoice that is not posted should not be able to generate pajak.io file"):
            draft_invoice._prepare_invoice_payload_pajakio()

        # Case 6: Invoice does not contain any taxes
        no_tax_invoice = self.init_invoice('out_invoice', partner=self.partner_a, products=self.product_a, taxes=[])
        no_tax_invoice.action_post()
        with self.assertRaises(UserError, msg="Invoice that does not contain any taxes should not be able to generate pajak.io file"):
            no_tax_invoice._prepare_invoice_payload_pajakio()

    def test_file_generation(self):
        """ Test to make sure when all criterias are fulfilled, it's able to generate the payload """
        payload = self.basic_invoice._prepare_invoice_payload_pajakio()
        self.assertTrue(payload)

        # Validate some attributes within payload
        self.assertEqual(payload["autoUploadDjp"], True)
        self.assertEqual(payload['noInvoice'], self.basic_invoice.name)
        self.assertEqual(payload['lawanTransaksi']['nitku'], '1234567890123456000000')  # NITKU = VAT + TKU

        # the 2 args: penandatangan and pembuatFaktur has to exist as they are critical to
        # the API request
        self.assertTrue(payload["penandatangan"])
        self.assertTrue(payload["pembuatFaktur"])

    def test_submission_approved(self):
        """ Test submission flow and assuming it's approved immediately

        If submission is successful, the response should contain some data returned by Pajak.io
        Then, we update fields in the invoice that is associated with Pajak.io
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(IAP_PROXY_METHOD, new=self._test_mock_invoice_request_approve):
            send_and_print.action_send_and_print()
            self.assertEqual(self.basic_invoice.l10n_id_pajakio_transaction_id, "1234567890")
            self.assertEqual(self.basic_invoice.l10n_id_pajakio_status, "approved")

    def test_submission_pending(self):
        """ Test submission flow and it is pending approval """

        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(IAP_PROXY_METHOD, new=self._test_mock_invoice_request_pending):
            send_and_print.action_send_and_print()
            self.assertEqual(self.basic_invoice.l10n_id_pajakio_transaction_id, "1234567890")
            self.assertEqual(self.basic_invoice.l10n_id_pajakio_status, "waiting")

    # =========================
    # Mocked IAP request result
    # =========================

    def _test_mock_invoice_request_approve(self, params, url_path, timeout=30):
        if url_path == "/api/pajakio/1/create_invoice":
            return {
                "data": {
                    "transactionId": "1234567890",
                    "noInvoice": "demosandbox openAPI CTAS 202401-1",
                }
            }
        elif url_path == "/api/pajakio/1/update":
            return {
                "data": {
                    "1234567890": {
                        "status": "APPROVAL_SUKSES",
                        "data": {
                            "status": "APPROVAL_SUKSES",
                            "keteranganDjp": ""
                        }
                    }
                }
            }

    def _test_mock_invoice_request_pending(self, params, url_path, timeout=30):
        if url_path == "/api/pajakio/1/create_invoice":
            return {
                "data": {
                    "transactionId": "1234567890",
                    "noInvoice": "demosandbox openAPI CTAS 202401-1",
                }
            }
        elif url_path == "/api/pajakio/1/update":
            return {
                "data": {
                    "1234567890": {
                        "status": "MENUNGGU_VERIFIKASI_DJP",
                        "data": {
                            "status": "MENUNGGU_VERIFIKASI_DJP",
                        }
                    }
                }
            }
