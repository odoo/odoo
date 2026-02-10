from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import HttpCase, tagged, freeze_time
from odoo.tools import mute_logger

from odoo.addons.account_peppol.tests.common import PeppolConnectorCommon
from odoo.addons.account_peppol.tools.peppol_iap_connector import PeppolIAPConnector


@freeze_time('2026-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolKYC(PeppolConnectorCommon, HttpCase):

    def _mock_can_connect_method(self, with_auth=False):
        auth_vals = {'available_auths': {'itsme': {'authorization_url': 'test_authorization_url'}}} if with_auth else {}
        return patch('odoo.addons.account_peppol.tools.peppol_iap_connector.PeppolIAPConnector.can_connect', return_value={
            'auth_required': with_auth,
            **auth_vals,
        })

    def _mock_create_connection_method(self, id_client='test_id_client', peppol_state='smp_registration'):
        return patch('odoo.addons.account_peppol.tools.peppol_iap_connector.PeppolIAPConnector.create_connection', return_value={
            'id_client': id_client, 'refresh_token': 'test_refresh_token', 'peppol_state': peppol_state
        })

    def test_connect_no_kyc(self):
        company = self.env.company
        eas, endpoint = '0208', '0239843188'
        peppol_identifier = f'{eas}:{endpoint}'
        with self._mock_requests([
            self._mock_lookup_participant(),
            self._mock_can_connect(with_auth=False), self._mock_connect(),
        ]):
            wizard = self.env['peppol.registration'].create({
                'peppol_eas': eas,
                'peppol_endpoint': endpoint,
                'phone_number': '+32483123456',
                'contact_email': 'yourcompany@example.com',
            })
            self.assertTrue(wizard.smp_registration)
            self.assertEqual(wizard.peppol_can_connect_data, {'auth_required': False})
            self.assertFalse(wizard.display_itsme_login)
            self.assertTrue(wizard.display_no_auth_buttons)
            wizard.button_register_peppol_participant()
        self.assertEqual(company.account_peppol_proxy_state, 'smp_registration')
        self.assertRecordValues(company.account_peppol_edi_user, [{
            'edi_identification': peppol_identifier,
            'edi_mode': 'test',
            'proxy_type': 'peppol',
        }])

    def test_connect_with_itsme_successful_auth(self):
        company = self.env.company
        self.authenticate('admin', 'admin')
        eas, endpoint = '0208', '0239843188'
        with (
            self._mock_requests([
                self._mock_lookup_participant(),
            ]),
            self._mock_can_connect_method(with_auth=True) as mocked_can_connect,
        ):
            wizard = self.env['peppol.registration'].create({
                'peppol_eas': '0208',
                'peppol_endpoint': '0239843188',
                'phone_number': '+32483123456',
                'contact_email': 'yourcompany@example.com',
            })
            self.assertTrue(wizard.smp_registration)
            self.assertEqual(wizard.peppol_can_connect_data, {
                'auth_required': True,
                'available_auths': {
                    'itsme': {'authorization_url': 'test_authorization_url'},
                },
            })
            self.assertTrue(wizard.display_itsme_login)
            self.assertFalse(wizard.display_no_auth_buttons)
            result = wizard.button_register_peppol_participant(selected_auth='itsme')
            connect_token = mocked_can_connect.call_args.kwargs['connect_token']
        self.assertEqual(result, {'type': 'ir.actions.act_url', 'url': 'test_authorization_url', 'target': 'new'})
        self.assertEqual(company.account_peppol_proxy_state, 'not_registered')

        # a window is opened with the url above, the KYC flow happens and calls back
        with (
            self._mock_create_connection_method() as connect_mock,
        ):
            response = self.url_open('/peppol/authentication/callback', method='GET', params={
                'auth_type': 'itsme',
                'connect_token': connect_token,
                'auth_token': 'test_auth_token',
            })
        self.assertTrue(response.history[0].is_redirect)
        self.assertEqual(response.status_code, 200)
        # callback-action closes the window opened for the authentication and displays a notification
        self.assertIn('/odoo/peppol-auth-callback-action?success=True', response.url)
        connect_mock.assert_called_once()
        self.assertEqual(company.account_peppol_proxy_state, 'smp_registration')
        self.assertRecordValues(company.account_peppol_edi_user, [{
            'edi_identification': f'{eas}:{endpoint}',
            'edi_mode': 'test',
            'proxy_type': 'peppol',
        }])

    def test_connect_with_itsme_failed_auth_case_1(self):
        """
        Checks that if somehow the button_register_peppol_participant is called without
        authentication first when it is necessary, the route raises an error.
        """
        company = self.env.company
        with self._mock_requests([
            self._mock_lookup_participant(),
            self._mock_can_connect(with_auth=True),
        ]):
            wizard = self.env['peppol.registration'].create({
                'peppol_eas': '0208',
                'peppol_endpoint': '0239843188',
                'phone_number': '+32483123456',
                'contact_email': 'yourcompany@example.com',
            })
            self.assertTrue(wizard.smp_registration)
            self.assertEqual(wizard.peppol_can_connect_data, {
                'auth_required': True,
                'available_auths': {
                    'itsme': {'authorization_url': 'test_authorization_url'},
                },
            })
            self.assertTrue(wizard.display_itsme_login)
            self.assertFalse(wizard.display_no_auth_buttons)
            with self.assertRaisesRegex(UserError, "You need to authenticate to continue."):
                wizard.button_register_peppol_participant()
        self.assertEqual(company.account_peppol_proxy_state, 'not_registered')
        self.assertFalse(company.account_peppol_edi_user)

    @mute_logger('odoo.addons.account_peppol.controllers.authentication')
    def test_connect_with_itsme_failed_auth_case_2(self):
        company = self.env.company
        self.authenticate('admin', 'admin')
        with self._mock_can_connect_method(with_auth=True) as mocked_can_connect:
            wizard = self.env['peppol.registration'].create({
                'peppol_eas': '0208',
                'peppol_endpoint': '0239843188',
                'phone_number': '+32483123456',
                'contact_email': 'yourcompany@example.com',
            })
            self.assertTrue(wizard.smp_registration)
            self.assertEqual(wizard.peppol_can_connect_data, {
                'auth_required': True,
                'available_auths': {
                    'itsme': {'authorization_url': 'test_authorization_url'},
                },
            })
            self.assertTrue(wizard.display_itsme_login)
            self.assertFalse(wizard.display_no_auth_buttons)
            result = wizard.button_register_peppol_participant(selected_auth='itsme')
            connect_token = mocked_can_connect.call_args.kwargs['connect_token']

        self.assertEqual(result, {'type': 'ir.actions.act_url', 'url': 'test_authorization_url', 'target': 'new'})
        self.assertEqual(company.account_peppol_proxy_state, 'not_registered')

        with self._mock_create_connection_method() as connect_mock:
            response = self.url_open('/peppol/authentication/callback', method='GET', params={
                'auth_type': 'itsme',
                'connect_token': connect_token,
                'auth_token': None,  # the authentication failed!
            })
        self.assertTrue(response.history[0].is_redirect)
        self.assertEqual(response.status_code, 200)
        self.assertIn('/odoo/peppol-auth-callback-action?success=False', response.url)
        connect_mock.assert_not_called()
        self.assertEqual(company.account_peppol_proxy_state, 'not_registered')
        self.assertFalse(company.account_peppol_edi_user)

    def test_connector_fails_in_demo(self):
        company = self.env.company
        self.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'demo')
        with self.assertRaises(AssertionError):
            PeppolIAPConnector(company)
