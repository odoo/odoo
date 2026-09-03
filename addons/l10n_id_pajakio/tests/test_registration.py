from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

IAP_PROXY_METHOD = "odoo.addons.l10n_id_pajakio.models.iap_account.IapAccount._l10n_id_pajakio_iap_connect"
IAP_PROXY_JSONRPC = "odoo.addons.l10n_id_pajakio.models.iap_account.jsonrpc"


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPajakio(AccountTestInvoicingCommon):
    """ Tests for the user/company registration and activation flows"""

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].update({
            'country_id': cls.env.ref('base.id').id,
            'city': 'Jakarta',
            'vat': '1234567890123456',
            'l10n_id_pajakio_mode': 'test',
        })
        # l10n_id_pajakio_key_identifier is groups=fields.NO_ACCESS, so it can only be read/written via sudo()
        # variable created for the test class to avoid calling sudo() throughout all methods
        cls.company_sudo = cls.company_data['company'].sudo()

        # mocked return arguments
        cls.mock_register_user_success = {
            "data": {
                "key_identifier": "mockKeyIdentifier",
            },
        }
        cls.mock_register_user_fail = {
            "error": "Email already registered",
            "code": "register_user_failed",
        }
        cls.mock_register_company_success = {
            'data': {
                'clientId': 'mockClientId',
            },
        }
        cls.mock_register_company_fail = {
            'error': "Failed to register company in Pajak.io: PASSWORD DOESN'T MATCH WITH REGISTERED EMAIL",
            'code': 'register_company_failed',
        }
        cls.mock_sign_in_success = {
            'data': {
                'clientId': 'mockClientId',
                'key_identifier': 'mockKeyIdentifier',
            },
        }
        cls.mock_sign_in_fail = {
            'error': "NPWP is not registered in Pajak.io",
            'code': 'sign_in_failed',
        }
        cls.mock_activation_success = {
            "data": True,
        }

    def test_iap_connect_params_for_jsonrpc(self):
        """Test behaviour of _l10n_id_pajakio_iap_connect, by checkig arguments in the method call and the return value"""
        self.company_sudo.l10n_id_pajakio_key_identifier = 'test_key_identifier'

        account = self.env['iap.account'].sudo().get('l10n_id_pajakio_proxy')
        account.account_token = 'test_account_token'

        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')

        with patch(IAP_PROXY_JSONRPC, return_value={'data': 'ok'}) as mock_jsonrpc:
            result = self.env['iap.account']._l10n_id_pajakio_iap_connect({}, '/api/pajakio/1/some_route')

        # Will return exactly result of jsonrpc
        self.assertEqual(result, {'data': 'ok'})

        mock_jsonrpc.assert_called_once()
        url, kwargs = mock_jsonrpc.call_args.args[0], mock_jsonrpc.call_args.kwargs
        self.assertEqual(url, 'https://iap-services.odoo.com/api/pajakio/1/some_route')

        # key_identifier is sent by default; account_token are not
        self.assertEqual(kwargs['params'], {
            'mode': 'test',
            'key_identifier': 'test_key_identifier',
            'dbuuid': dbuuid,
        })

        # account_token is only sent when explicitly requested
        with patch(IAP_PROXY_JSONRPC, return_value={}) as mock_jsonrpc:
            self.env['iap.account']._l10n_id_pajakio_iap_connect({}, '/some_route', include_account_token=True)
        self.assertEqual(mock_jsonrpc.call_args.kwargs['params']['account_token'], 'test_account_token')

        # key_identifier is not sent when not explicitly requested
        with patch(IAP_PROXY_JSONRPC, return_value={}) as mock_jsonrpc:
            self.env['iap.account']._l10n_id_pajakio_iap_connect({}, '/some_route', include_key_identifier=False)
        self.assertNotIn('key_identifier', mock_jsonrpc.call_args.kwargs['params'])

        # IAP service endpoint will change based on the `l10n_id_pajakio.endpoint` system parameter
        self.env['ir.config_parameter'].sudo().set_param('l10n_id_pajakio.endpoint', 'https://custom.example.com')
        with patch(IAP_PROXY_JSONRPC, return_value={}) as mock_jsonrpc:
            self.env['iap.account']._l10n_id_pajakio_iap_connect({}, '/some_route')

        self.assertEqual(mock_jsonrpc.call_args.args[0], 'https://custom.example.com/some_route')

    # User Registration

    def test_pajakio_register_user_success(self):
        """Test when a user successfully registers user, the company's email and key_identifier are set"""
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'mode': 'register_user',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'user_name': 'John Doe',
            'phone': '1234567890',
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_register_user_success) as mock_method:
            self.assertFalse(self.company_data['company'].l10n_id_pajakio_email)
            wizard.action_register_user()
            self.assertEqual(mock_method.call_count, 1)
            self.assertEqual(self.company_data['company'].l10n_id_pajakio_email, 'test@example.com')
            self.assertEqual(self.company_sudo.l10n_id_pajakio_key_identifier, 'mockKeyIdentifier')

    def test_pajakio_register_user_fail(self):
        """Test when a user failed to register user, raise UserError"""
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'mode': 'register_user',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'user_name': 'John Doe',
            'phone': '1234567890',
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_register_user_fail) as mock_method:
            self.assertFalse(self.company_data['company'].l10n_id_pajakio_email)
            with self.assertRaises(UserError):
                wizard.action_register_user()
            self.assertEqual(mock_method.call_count, 1)
            self.assertFalse(self.company_data['company'].l10n_id_pajakio_email)

    # Company Registration

    def test_pajakio_register_company_success(self):
        """Test that when company registers successfully, we mark the company as registered"""
        self.company_data['company'].l10n_id_pajakio_email = 'test@example.com'
        self.company_sudo.l10n_id_pajakio_key_identifier = 'mock_key_identifier'
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'mode': 'register_company',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'company_name': 'Test Company',
            'npwp': '1234567890',
            'address': 'Test Address',
            'city': 'Jakarta',
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_register_company_success) as mock_method:
            wizard.action_register_company()
            self.assertEqual(mock_method.call_count, 2)
            self.assertTrue(self.company_data['company'].l10n_id_pajakio_company_registered)
            self.assertEqual(self.company_sudo.l10n_id_pajakio_key_identifier, 'mock_key_identifier')

    def test_pajakio_register_company_fail(self):
        """Test if company registration fail, an exception should be raised"""
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'mode': 'register_company',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'company_name': 'Test Company',
            'npwp': '1234567890',
            'address': 'Test Address',
            'city': 'Jakarta',
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_register_company_fail) as mock_method:
            with self.assertRaises(UserError):
                wizard.action_register_company()
            self.assertEqual(mock_method.call_count, 1)
            self.assertFalse(self.company_data['company'].l10n_id_pajakio_company_registered)
            self.assertFalse(self.company_sudo.l10n_id_pajakio_key_identifier)

    # Sign in

    def test_action_sign_in_pajakio_opens_wizard_with_context(self):
        """Test that when the sign in wizard opens, the default email and npwp are pre-filled from the company record"""
        company = self.company_data['company']
        company.write({
            'email': 'signin@example.com',
            'vat': '1234567890123456',
        })
        settings = self.env['res.config.settings'].create({})
        action = settings.action_sign_in_pajakio()
        self.assertEqual(action['context']['default_mode'], 'sign_in')
        self.assertEqual(action['context']['default_email'], company.email)
        self.assertEqual(action['context']['default_npwp'], company.vat)

    def test_pajakio_sign_in_success(self):
        """Test sign in stores email and key_identifier used from the wizard on company record,
        and marks the company as registered"""
        company_id = self.company_data['company']
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'mode': 'sign_in',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'npwp': '1234567890',
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_sign_in_success) as mock_method:
            self.assertFalse(company_id.l10n_id_pajakio_email)
            self.assertFalse(self.company_sudo.l10n_id_pajakio_key_identifier)
            wizard.action_sign_in()
            self.assertEqual(mock_method.call_count, 2)  # since sign in is followed with activation immediately, there's 2 API calls
            self.assertEqual(company_id.l10n_id_pajakio_email, 'test@example.com')
            self.assertEqual(self.company_sudo.l10n_id_pajakio_key_identifier, 'mockKeyIdentifier')
            self.assertTrue(company_id.l10n_id_pajakio_company_registered)

    def test_pajakio_sign_in_fail(self):
        """Test sign in failure raises an error and it shouldn't store any credentials on company record"""
        company_id = self.company_data['company']
        wizard = self.env['l10n_id_pajakio.registration.form'].create({
            'mode': 'sign_in',
            'email': 'test@example.com',
            'password': 'SecurePassword123!',
            'npwp': '1234567890',
        })
        with patch(IAP_PROXY_METHOD, return_value=self.mock_sign_in_fail) as mock_method:
            with self.assertRaises(UserError):
                wizard.action_sign_in()
            self.assertEqual(mock_method.call_count, 1)  # once sign in fails, activation should not be called
            self.assertFalse(company_id.l10n_id_pajakio_email)
            self.assertFalse(self.company_sudo.l10n_id_pajakio_key_identifier)

    # company activation and logout

    def test_pajakio_activate_pajakio_success(self):
        """Activate pajak.io connection, should set `l10n_id_pajakio_active` to True"""
        company_id = self.company_data['company']
        company_id.l10n_id_pajakio_email = 'test@email.com'
        self.company_sudo.l10n_id_pajakio_key_identifier = 'key_identifier'

        self.assertFalse(company_id.l10n_id_pajakio_active)
        with patch(IAP_PROXY_METHOD, return_value=self.mock_activation_success) as mock_method:
            company_id._l10n_id_pajakio_activate()
            self.assertEqual(mock_method.call_count, 1)
            self.assertEqual(mock_method.call_args[0][1], "/api/pajakio/1/register")
            self.assertTrue(company_id.l10n_id_pajakio_active)

    def test_pajakio_logout_clear_credentials(self):
        """Logout clears all the credentials setup previously"""
        company = self.company_data['company']
        company.l10n_id_pajakio_email = 'test@email.com'
        self.company_sudo.l10n_id_pajakio_key_identifier = 'key_identifier'
        company.l10n_id_pajakio_company_registered = True
        company.l10n_id_pajakio_active = True

        settings = self.env['res.config.settings'].create({})
        # it only clears the credentials but will not call IAP
        with patch(IAP_PROXY_METHOD, return_value=self.mock_activation_success) as mock_iap:
            settings.action_logout_pajakio()
            mock_iap.assert_not_called()

        self.assertFalse(company.l10n_id_pajakio_active)
        self.assertFalse(company.l10n_id_pajakio_email)
        self.assertFalse(self.company_sudo.l10n_id_pajakio_key_identifier)
        self.assertFalse(company.l10n_id_pajakio_company_registered)
