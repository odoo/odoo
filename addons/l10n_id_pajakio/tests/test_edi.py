import json

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from unittest.mock import call, patch

IAP_PROXY_METHOD = "odoo.addons.l10n_id_pajakio.models.iap_account.IapAccount._l10n_id_pajakio_iap_connect"

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPajakio(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].update({
            'country_id': cls.env.ref('base.id').id,
            'city': 'Jakarta',
            'vat': '1234567890123456',
            'l10n_id_pajakio_mode': 'test'
        })

        # mocked return arguments
        cls.mock_register_user_success = {
            "data": None
        }
        cls.mock_register_user_fail = {
            "error": "Email already registered",
            "code": "register_user_failed",
        }
        cls.mock_register_company_success = {
            'data': {
                'clientId': '-vvQZu6NgRStS-QNIJB9gG7aGt12v72fPg'
            }
        }
        cls.mock_register_company_fail = {
            'error': "Failed to register company in Pajak.io: PASSWORD DOESN'T MATCH WITH REGISTERED EMAIL",
            'code': 'register_company_failed'
        }
        cls.mock_sign_in_success = {
            'data': {
                'clientId': '-vvQZu6NgRStS-QNIJB9gG7aGt12v72fPg'
            }
        }
        cls.mock_sign_in_fail = {
            'error': "NPWP is not registered in Pajak.io",
            'code': 'sign_in_failed'
        }
        cls.mock_activation_success = {
            "data": True
        }

    def test_pajakio_register_user_success(self):
        """ Test when a user successfully registers user, the company's email is supposed to be set"""
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'user_name': 'John Doe',
            'phone': '1234567890'
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_register_user_success) as mock_method:
            self.assertFalse(self.company_data['company'].l10n_id_pajakio_test_email)
            wizard.action_register_user()
            self.assertEqual(mock_method.call_count, 1)
            self.assertEqual(self.company_data['company'].l10n_id_pajakio_test_email, 'test@example.com')

    def test_pajakio_register_user_fail(self):
        """ Test when a user failed to register user, an error should be raise and exception should be caught and
        the erro message should contain the reason"""
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'user_name': 'John Doe',
            'phone': '1234567890'
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_register_user_fail) as mock_method:
            self.assertFalse(self.company_data['company'].l10n_id_pajakio_test_email)
            with self.assertRaises(UserError):
                wizard.action_register_user()
            self.assertEqual(mock_method.call_count, 1)
            self.assertFalse(self.company_data['company'].l10n_id_pajakio_test_email)  # should remain false since registration fails

    def test_pajakio_register_company_success(self):
        """ Test that when company successfuly is registered, response is supposed to contain clientId which we will store"""
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'company_name': 'Test Company',
            'npwp': '1234567890',
            'address': 'Test Address',
            'city': 'Jakarta'
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_register_company_success) as mock_method:
            wizard.action_register_company()
            self.assertEqual(mock_method.call_count, 1)
            self.assertEqual(self.company_data['company'].l10n_id_pajakio_test_client_id, '-vvQZu6NgRStS-QNIJB9gG7aGt12v72fPg')

    def test_pajakio_register_company_fail(self):
        """ Test if company registration fail, an exception should be raised"""
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'company_name': 'Test Company',
            'npwp': '1234567890',
            'address': 'Test Address',
            'city': 'Jakarta'
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_register_company_fail) as mock_method:
            with self.assertRaises(UserError):
                wizard.action_register_company()
            self.assertEqual(mock_method.call_count, 1)


    def test_action_pajakio_register_company_opens_wizard_in_test_mode(self):
        """Settings action opens company registration wizard with test email and NPWP defaults."""
        company = self.company_data['company']
        company.l10n_id_pajakio_test_email = 'test@example.com'
        company.vat = '1234567890123456'

        settings = self.env['res.config.settings'].create({})
        action = settings.action_pajakio_register_company()
        self.assertEqual(action['res_model'], 'l10n_id_pajakio.registration.form')
        self.assertTrue(action['context']['register_company'])
        self.assertEqual(action['context']['default_email'], 'test@example.com')
        self.assertEqual(action['context']['default_npwp'], '1234567890123456')

    def test_action_pajakio_register_company_opens_wizard_in_prod_mode(self):
        """Settings action uses production email when integration mode is prod."""
        company = self.company_data['company']
        company.write({
            'l10n_id_pajakio_mode': 'prod',
            'l10n_id_pajakio_email': 'prod@example.com',
        })
        settings = self.env['res.config.settings'].create({})
        action = settings.action_pajakio_register_company()
        self.assertEqual(action['context']['default_email'], 'prod@example.com')
        self.assertEqual(action['context']['default_npwp'], company.vat)

    def test_action_sign_in_pajakio_opens_wizard_with_context(self):
        """Settings sign-in action opens wizard with sign_in flag and company email/VAT defaults."""
        company = self.company_data['company']
        company.write({
            'email': 'signin@example.com',
            'vat': '1234567890123456',
        })
        settings = self.env['res.config.settings'].create({})
        action = settings.action_sign_in_pajakio()
        self.assertTrue(action['context']['sign_in'])
        self.assertEqual(action['context']['default_email'], company.email)
        self.assertEqual(action['context']['default_npwp'], company.vat)

    def test_pajakio_sign_in_success(self):
        """ Test sign in stores email and client ID on success."""
        company_id = self.company_data['company']
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'npwp': '1234567890',
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_sign_in_success) as mock_method:
            self.assertFalse(company_id.l10n_id_pajakio_test_email)
            self.assertFalse(company_id.l10n_id_pajakio_test_client_id)
            wizard.action_sign_in()
            self.assertEqual(mock_method.call_count, 1)
            self.assertEqual(company_id.l10n_id_pajakio_test_email, 'test@example.com')
            self.assertEqual(company_id.l10n_id_pajakio_test_client_id, '-vvQZu6NgRStS-QNIJB9gG7aGt12v72fPg')

    def test_pajakio_sign_in_fail(self):
        """ Test sign in failure raises an error and does not store credentials."""
        company_id = self.company_data['company']
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'npwp': '1234567890',
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_sign_in_fail) as mock_method:
            with self.assertRaises(UserError):
                wizard.action_sign_in()
            self.assertEqual(mock_method.call_count, 1)
            self.assertFalse(company_id.l10n_id_pajakio_test_email)
            self.assertFalse(company_id.l10n_id_pajakio_test_client_id)

    def test_pajakio_activate_requires_email_and_client_id(self):
        """ email and client_id needs to be configured before being allowed to proceed """
        company_id = self.company_data['company']
        with self.assertRaises(UserError):
            company_id._l10n_id_pajakio_activate()

        company_id._l10n_id_pajakio_set_email('test@email.com')

        # should still produce error because client_id is not set
        with self.assertRaises(UserError):
            company_id._l10n_id_pajakio_activate()

        company_id._l10n_id_pajakio_set_email('')
        company_id._l10n_id_pajakio_set_client_id('client_id')

        with self.assertRaises(UserError):
            company_id._l10n_id_pajakio_activate()

    def test_pajakio_activate_pajakio_success(self):
        """ Activate pajak.io connection, should set `l10n_id_pajakio_active` to False"""
        company_id = self.company_data['company']
        company_id._l10n_id_pajakio_set_email('test@email.com')
        company_id._l10n_id_pajakio_set_client_id('client_id')

        self.assertFalse(company_id.l10n_id_pajakio_active)
        with patch(IAP_PROXY_METHOD, return_value=self.mock_activation_success) as mock_method:
            company_id._l10n_id_pajakio_activate()
            self.assertEqual(mock_method.call_count, 1)
            self.assertEqual(mock_method.call_args[0][1], "/api/pajakio/1/register")
            self.assertTrue(company_id.l10n_id_pajakio_active)

    def test_pajakio_deactivate_pajakio_success(self):
        """ Deactivate pajak.io connection, should set `l10n_id_pajakio_active` to False."""
        company_id = self.company_data['company']
        company_id._l10n_id_pajakio_set_email('test@email.com')
        company_id._l10n_id_pajakio_set_client_id('client_id')

        # Simulate currently activated company
        company_id.l10n_id_pajakio_active = True
        self.assertTrue(company_id.l10n_id_pajakio_active)

        with patch(IAP_PROXY_METHOD, return_value=self.mock_activation_success) as mock_method:
            company_id._l10n_id_pajakio_activate(status=False)
            self.assertEqual(mock_method.call_count, 1)
            self.assertEqual(mock_method.call_args[0][1], "/api/pajakio/1/unregister")
            self.assertFalse(company_id.l10n_id_pajakio_active)

@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nIDTestPajakioEdi(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].update({
            "name": "ID Company",
            'country_id': cls.env.ref('base.id').id,
            'city': 'Jakarta',
            'vat': '1234567890123456',
            # assumes that account has been successfully registered and activated
            'l10n_id_pajakio_mode': 'test',
            'l10n_id_pajakio_active': True,
            'l10n_id_pajakio_test_client_id': 'client_id',
            'l10n_id_pajakio_test_email': 'test@email.com',
        })
        cls.partner_a.write({
            'l10n_id_kode_transaksi': '04',
            'vat': '1234567890123456',
            'country_id': cls.env.ref('base.id').id,
            'l10n_id_pkp': True,
        })

    def test_pajakio_edi_shows(self):
        """ Test when the Pajak.io EDI option is shown in the invoice send wizard"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True)
        wizard = self.create_send_and_print(invoice)
        self.assertIn('id_pajakio', wizard.extra_edis)

    def test_pajakio_edi_not_shown(self):
        # pajak.io not activated yet
        self.company_data['company'].l10n_id_pajakio_active = False

        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True)
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

        # The pajak.io status of invoice is either draft/waiting/approved
        self.company_data['company'].l10n_id_pajakio_active = True

        invoice.l10n_id_pajakio_status = 'draft'
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

        invoice.l10n_id_pajakio_status = 'waiting'
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

        invoice.l10n_id_pajakio_status = 'approved'
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

    def test_pajakio_edi_generate_json_errors(self):
        """Test that errors are raised when invoice or partner eligibility conditions are not met."""

        # 1. Company has no NPWP
        self.company_data['company'].vat = False
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        with self.assertRaisesRegex(Exception, "NPWP"):
            invoice._prepare_invoice_payload_pajakio()

        # 2. Company has no city configured
        self.company_data['company'].vat = '1234567890123456'
        self.company_data['company'].city = False
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        with self.assertRaisesRegex(Exception, "city"):
            invoice._prepare_invoice_payload_pajakio()

        # 3. Customer is not taxable (no l10n_id_pkp)
        self.company_data['company'].city = "Jakarta"
        self.partner_a.l10n_id_pkp = False
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        with self.assertRaisesRegex(Exception, "not taxable"):
            invoice._prepare_invoice_payload_pajakio()
        self.partner_a.l10n_id_pkp = True  # restore for next

        # 4. Customer lacks document number for non-TIN type
        self.partner_a.l10n_id_buyer_document_type = 'Passport'
        self.partner_a.l10n_id_buyer_document_number = False
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        with self.assertRaisesRegex(Exception, "Document number.*hasn't been filled in"):
            invoice._prepare_invoice_payload_pajakio()
        self.partner_a.l10n_id_buyer_document_type = 'TIN'  # restore

        # 5. Customer has no NPWP (VAT)
        self.partner_a.vat = False
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        with self.assertRaisesRegex(Exception, "NPWP for customer"):
            invoice._prepare_invoice_payload_pajakio()
        self.partner_a.vat = '1234567890123456'  # restore

        # 6. Customer has no country
        self.partner_a.country_id = False
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        with self.assertRaisesRegex(Exception, "No country is set"):
            invoice._prepare_invoice_payload_pajakio()
        self.partner_a.country_id = self.env.ref('base.id')  # restore

        # 7. Invoice is in draft state
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=False, taxes=self.tax_sale_a)
        with self.assertRaisesRegex(Exception, "draft state"):
            invoice._prepare_invoice_payload_pajakio()
        invoice.action_post()

        # 8. Not an Indonesian company (country_code != "ID")
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.country_code = "SG"
        with self.assertRaisesRegex(Exception, "not under Indonesian company"):
            invoice._prepare_invoice_payload_pajakio()
        invoice.country_code = "ID"  # restore

        # 9. Not an invoice (move_type != 'out_invoice')
        invoice = self.init_invoice("in_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        with self.assertRaisesRegex(Exception, "not an invoice"):
            invoice._prepare_invoice_payload_pajakio()

        # 10. Invoice has no taxes
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=[])
        with self.assertRaisesRegex(Exception, "does not contain any taxes"):
            invoice._prepare_invoice_payload_pajakio()

        # 11. For kode transaksi 07, missing required fields
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_kode_transaksi = "07"
        invoice.l10n_id_coretax_add_info_07 = False
        invoice.l10n_id_coretax_facility_info_07 = False
        with self.assertRaisesRegex(Exception, "Kode 07"):
            invoice._prepare_invoice_payload_pajakio()

        # 12. For kode transaksi 08, missing required fields
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_kode_transaksi = "08"
        invoice.l10n_id_coretax_add_info_08 = False
        invoice.l10n_id_coretax_facility_info_08 = False
        with self.assertRaisesRegex(Exception, "Kode 08"):
            invoice._prepare_invoice_payload_pajakio()


    def test_pajakio_edi_generate_json(self):
        """ Test the JSON data created by method _prepare_invoice_payload_pajakio is correct """
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_kode_transaksi = "04"
        # Make sure draft is not blocking eligibility (should be posted already)
        payload = invoice._prepare_invoice_payload_pajakio()

        # Validate some important fields in the generated payload structure
        self.assertEqual(payload["noInvoice"], invoice.name)
        self.assertEqual(payload["kdJenisTransaksi"], 'TD.00304')
        self.assertIn("lawanTransaksi", payload)
        self.assertEqual(payload["lawanTransaksi"]["identityType"], "NPWP")
        self.assertEqual(payload["lawanTransaksi"]["identityValue"], invoice.partner_id.commercial_partner_id.vat)
        self.assertEqual(payload["penandatangan"]["nama"], "ID Company")
        self.assertEqual(payload["penandatangan"]["npwp"], "1234567890123456")

        # Check a line for expected structure and value conversion
        self.assertIsInstance(payload["barangJasa"], list)
        self.assertTrue(len(payload["barangJasa"]) > 0)
        line = payload["barangJasa"][0]
        self.assertIn("jenis", line)
        self.assertIn("kode", line)
        self.assertIn("nama", line)
        # Instead of data type, check the actual amount
        self.assertEqual(line["harga"], 1000.0)

        # Some specific checks for kode transaksi 04
        self.assertTrue(line["cekDppLain"])
        # The DPP Lain and standard DPP should be calculated based on value
        self.assertEqual(line["dpp"], 1000.0)
        self.assertEqual(line["dppLain"], 916.67)

    def test_pajakio_generate_json_attachment_data(self):
        """ Test _l10n_id_pajakio_generate_json creates expected attachment payload in invoice_data."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_kode_transaksi = "04"

        invoice_data = {
            'extra_edis': {'id_pajakio'},
        }
        expected_payload = invoice._prepare_invoice_payload_pajakio()

        self.env['account.move.send']._l10n_id_pajakio_generate_json(invoice, invoice_data)

        self.assertIn('pajakio_attachments', invoice_data)
        attachment_data = invoice_data['pajakio_attachments']
        self.assertEqual(attachment_data['name'], f'{invoice.name}_pajakio_request.json')
        self.assertEqual(attachment_data['mimetype'], 'application/json')
        self.assertEqual(attachment_data['res_model'], 'account.move')
        self.assertEqual(attachment_data['res_field'], 'l10n_id_pajakio_file')
        self.assertEqual(json.loads(attachment_data['raw']), expected_payload)

    def test_pajakio_send_invoice_success(self):
        """Test for method _l10n_id_pajakio_send: should store transaction ID on invoice if successful """
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        json_content = invoice._prepare_invoice_payload_pajakio()

        mock_response = {'data': {'transactionId': 'TRX-12345'}}
        with patch(IAP_PROXY_METHOD, return_value=mock_response) as mock_iap:
            result = invoice._l10n_id_pajakio_send(json_content)
            self.assertFalse(result)
            self.assertEqual(invoice.l10n_id_pajakio_transaction_id, 'TRX-12345')
            self.assertEqual(mock_iap.call_args[0][1], "/api/pajakio/1/create_invoice")

    def test_pajakio_send_invoice_error(self):
        """Test that _l10n_id_pajakio_send returns error message on failure. No transaction ID should be stored on
        the invoice as well"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        json_content = invoice._prepare_invoice_payload_pajakio()

        mock_response = {'error': 'Invalid payload'}
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            result = invoice._l10n_id_pajakio_send(json_content)
            self.assertEqual(result, 'Invalid payload')
            self.assertFalse(invoice.l10n_id_pajakio_transaction_id)

    def test_pajakio_update_status_approved(self):
        """Test that update_status sets approved status with invoice number and URL."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {
            'data': {
                'TRX-12345': {
                    'status': 'APPROVAL_SUKSES',
                    'data': {
                        'nofa': 'INV-001-DJP',
                        'urlPdf': 'https://pajak.io/receipt/TRX-12345.pdf',
                        'jenisFaktur': 'NORMAL',
                    }
                }
            }
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            result = invoice._l10n_id_pajakio_update_status()
            self.assertFalse(result)
            self.assertEqual(invoice.l10n_id_pajakio_status, 'approved')
            self.assertEqual(invoice.l10n_id_pajakio_invoice_number, 'INV-001-DJP')
            self.assertEqual(invoice.l10n_id_pajakio_transaction_url, 'https://pajak.io/receipt/TRX-12345.pdf')

    def test_pajakio_update_status_waiting(self):
        """Test that update_status sets waiting status."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {
            'data': {
                'TRX-12345': {
                    'status': 'MENUNGGU_VERIFIKASI_DJP',
                    'data': {'jenisFaktur': 'NORMAL'}
                }
            }
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            invoice._l10n_id_pajakio_update_status()
            self.assertEqual(invoice.l10n_id_pajakio_status, 'waiting')

    def test_pajakio_update_status_rejected(self):
        """Test that update_status sets rejected status with reason."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {
            'data': {
                'TRX-12345': {
                    'status': 'DITOLAK',
                    'data': {
                        'alasan': 'Invalid NPWP format',
                        'jenisFaktur': 'NORMAL',
                    }
                }
            }
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            invoice._l10n_id_pajakio_update_status()
            self.assertEqual(invoice.l10n_id_pajakio_status, 'rejected')
            self.assertEqual(invoice.l10n_id_pajakio_reject_reason, 'Invalid NPWP format')

    def test_pajakio_update_status_cancelled(self):
        """Test that update_status sets cancel status when jenisFaktur is BATAL."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {
            'data': {
                'TRX-12345': {
                    'status': 'APPROVAL_SUKSES',
                    'data': {'jenisFaktur': 'BATAL'}
                }
            }
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            invoice._l10n_id_pajakio_update_status()
            self.assertEqual(invoice.l10n_id_pajakio_status, 'cancel')

    # Cancel flow

    def test_pajakio_button_request_cancel_updates_status_to_cancel(self):
        """Requesting cancellation should call Pajak.io endpoints and update invoice status to cancel."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.write({
            'l10n_id_pajakio_status': 'approved',
            'l10n_id_pajakio_transaction_id': 'TRX-12345',
        })

        mock_cancel_response = {'data': True}
        mock_update_response = {
            'data': {
                'TRX-12345': {
                    'status': 'APPROVAL_SUKSES',
                    'data': {'jenisFaktur': 'BATAL'},
                }
            }
        }
        with (
            patch(IAP_PROXY_METHOD, side_effect=[mock_cancel_response, mock_update_response]) as mock_iap,
        ):
            invoice.button_request_cancel()

        self.assertEqual(invoice.l10n_id_pajakio_status, 'cancel')
        # the IAP method should be called twice, once for cancellation and another for update
        self.assertEqual(mock_iap.call_count, 2)
        self.assertEqual(
            mock_iap.call_args_list,
            [
                call({'transaction_ids': ['TRX-12345']}, '/api/pajakio/1/cancel_invoice'),
                call({'transaction_ids': ['TRX-12345']}, '/api/pajakio/1/update'),
            ],
        )

    def test_pajakio_button_request_cancel_raises_on_cancel_error(self):
        """Requesting cancellation should raise UserError when Pajak.io cancel API fails."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.write({
            'l10n_id_pajakio_status': 'approved',
            'l10n_id_pajakio_transaction_id': 'TRX-12345',
        })

        with (
            patch(IAP_PROXY_METHOD, return_value={'error': 'Cancellation rejected'}) as mock_iap,
        ):
            with self.assertRaises(UserError):
                invoice.button_request_cancel()

        self.assertEqual(mock_iap.call_count, 1)
        self.assertEqual(mock_iap.call_args[0][1], '/api/pajakio/1/cancel_invoice')

    def test_pajakio_button_request_cancel_logs_when_update_status_errors(self):
        """Cancellation success should log a warning message if status refresh fails."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.write({
            'l10n_id_pajakio_status': 'approved',
            'l10n_id_pajakio_transaction_id': 'TRX-12345',
        })

        with (
            patch(IAP_PROXY_METHOD, side_effect=[{'data': True}, {'error': 'Connection timeout'}]) as mock_iap,
        ):
            invoice.button_request_cancel()

        # Should be called twice, no error is raised but latest message should contain message that status update failed
        self.assertEqual(mock_iap.call_count, 2)
        self.assertEqual(mock_iap.call_args_list[0], call({'transaction_ids': ['TRX-12345']}, '/api/pajakio/1/cancel_invoice'))
        self.assertEqual(mock_iap.call_args_list[1], call({'transaction_ids': ['TRX-12345']}, '/api/pajakio/1/update'))
        self.assertEqual(invoice.l10n_id_pajakio_status, 'approved')
        self.assertIn("unable to update status", invoice.message_ids[0].body)

    def test_pajakio_update_status_error_response(self):
        """Test that update_status returns error on IAP failure."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {'error': 'Connection timeout'}
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            result = invoice._l10n_id_pajakio_update_status()
            self.assertEqual(result, 'Connection timeout')

    def test_pajakio_rejected_invoice_can_be_resent(self):
        """Test that a rejected invoice is eligible for resending via pajak.io EDI."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True)
        invoice.l10n_id_pajakio_status = 'rejected'
        wizard = self.create_send_and_print(invoice)
        self.assertIn('id_pajakio', wizard.extra_edis)

    def test_pajakio_edi_not_applicable_for_non_invoice(self):
        """Test that pajak.io EDI is not applicable for refunds."""
        invoice = self.init_invoice("out_refund", partner=self.partner_a, amounts=[1000], post=True)
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)
