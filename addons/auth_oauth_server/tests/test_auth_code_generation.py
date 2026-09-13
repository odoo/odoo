import re
from urllib.parse import parse_qs, urlsplit, unquote

from odoo.tests import tagged

from .common import REDIRECT_URI, OauthServerCommon
from odoo.addons.auth_oauth_server_base.utils.oauth_utils import oauth_base_url


@tagged('post_install', '-at_install')
class TestAuthCodeGeneration(OauthServerCommon):

    def test_not_logged_in_user_is_redirected_to_login(self):
        response = self._authorize(allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn('/web/login', response.headers['Location'])

    def test_consent_screen_is_shown_and_not_frameable(self):
        self.authenticate('internal_user', 'internal_user')
        response = self._authorize()
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f"<strong>Test Client</strong> is requesting access to your Odoo account for <strong>{self.resource.label}</strong>",
            re.sub(r"\s+", " ", response.text)
        )
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertIn("frame-ancestors 'none'", response.headers.get('Content-Security-Policy', ''))

    def test_consent_approval_issues_code_with_iss(self):
        self.authenticate('internal_user', 'internal_user')

        response = self._submit_consent()
        self.assertEqual(response.status_code, 303)
        location = unquote(response.headers['Location'])
        self.assertTrue(location.startswith(REDIRECT_URI))
        self.assertIn('code=', location)
        self.assertIn(f'iss={oauth_base_url(self.env)}/oauth/{self.resource.name}', location)

    def test_consent_denial_redirects_with_access_denied(self):
        self.authenticate('internal_user', 'internal_user')
        response = self._submit_consent(allow='false')
        self.assertIn('error=access_denied', response.headers['Location'])

    def test_arbitrary_requested_scope_is_ignored(self):
        client_id = self._register_client()['client_id']
        self.authenticate('internal_user', 'internal_user')
        response = self._submit_consent(client_id=client_id, scope='read delete_everything')
        self.assertEqual(response.status_code, 303)

        client = self.env['oauth.client'].sudo().search([('client_id', '=', client_id)])
        auth_code = self.env['oauth.authorization.code']._retrieve_record(
            code=parse_qs(urlsplit(response.headers['Location']).query)['code'][0],
            client=client,
            redirect_uri=REDIRECT_URI,
        )
        self.assertEqual(auth_code.scope, self.resource.access_token_scope)

    def test_resource_group_restriction_is_enforced(self):
        self.authenticate('internal_user', 'internal_user')
        resource = self.env['oauth.resource'].sudo().create({
            'name': 'restricted', 'label': 'Restricted', 'access_token_scope': 'restricted',
            'allowed_group_ids': [self.env.ref('base.group_system').id],
        })
        client_id = self._register_client(resource=resource.name)['client_id']
        response = self._authorize(client_id=client_id)
        self.assertEqual(response.status_code, 400)

        response_json = response.json()
        self.assertEqual(response_json['error'], 'authorization_failed')
        self.assertEqual(response_json['error_description'], f"You do not have the required access rights for the '{resource.name}' resource.")

    def test_resource_access_is_checked_before_auth_code_generation(self):
        client_id = self._register_client()['client_id']
        self.authenticate('internal_user', 'internal_user')
        # internal_user has access, so authorize should render the consent screen.
        response = self._authorize(client_id=client_id)
        self.assertIn(
            f"<strong>Test Client</strong> is requesting access to your Odoo account for <strong>{self.resource.label}</strong>",
            re.sub(r"\s+", " ", response.text)
        )
        # The user was allowed when the consent screen was rendered, and loses access
        # before submitting the consent: the resource groups must be re-checked at submission,
        # otherwise a stale consent screen would still generate an authorization code.
        self.resource.allowed_group_ids = self.env.ref('base.group_system')

        response = self._submit_consent(client_id=client_id)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'authorization_failed')
        self.assertEqual(response_json['error_description'], f"You do not have the required access rights for the '{self.resource.name}' resource.")

        client = self.env['oauth.client'].search([('client_id', '=', client_id)])
        self.assertFalse(self.env['oauth.authorization.code'].search([('client_id', '=', client.id)]))

    def test_loopback_redirect_uri_matches_regardless_of_port(self):
        self.authenticate('internal_user', 'internal_user')
        client_id = self._register_client(redirect_uris=['http://127.0.0.1:8080/cb'])['client_id']
        response = self._authorize(client_id=client_id, redirect_uri='http://127.0.0.1:54321/cb')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'name="redirect_uri" value="http://127.0.0.1:54321/cb"',
            response.text
        )

    def test_loopback_redirect_uri_path_mismatch_rejection(self):
        self.authenticate('internal_user', 'internal_user')
        client_id = self._register_client(redirect_uris=['http://127.0.0.1:8080/cb'])['client_id']
        response = self._authorize(client_id=client_id, redirect_uri='http://127.0.0.1:54321/other')
        self.assertEqual(response.status_code, 400)

        response_json = response.json()
        self.assertEqual(response_json['error'], 'authorization_failed')
        self.assertEqual(response_json['error_description'], "redirect_uri is not registered for this client")

    def test_loopback_redirect_uri_query_mismatch_rejection(self):
        self.authenticate('internal_user', 'internal_user')
        client_id = self._register_client(redirect_uris=['http://127.0.0.1:8080/cb'])['client_id']
        response = self._authorize(client_id=client_id, redirect_uri='http://127.0.0.1:8080/cb?injected=1')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error_description'], "redirect_uri is not registered for this client")

    def test_redirect_uri_with_fragment_is_rejected(self):
        self.authenticate('internal_user', 'internal_user')
        client_id = self._register_client(redirect_uris=['http://127.0.0.1:8080/cb'])['client_id']
        response = self._authorize(client_id=client_id, redirect_uri='http://127.0.0.1:8080/cb#fragment')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error_description'], "redirect_uri is not registered for this client")

    def test_auth_code_is_appended_to_query_params(self):
        """A redirect_uri may already carry query params, which must stay intact"""
        self.authenticate('internal_user', 'internal_user')
        redirect_uri = 'https://client.example.com/cb?tenant=acme'
        client_id = self._register_client(redirect_uris=[redirect_uri])['client_id']

        for allow, expected_param in [('true', 'code='), ('false', 'error=access_denied')]:
            with self.subTest(allow=allow):
                response = self._submit_consent(client_id=client_id, redirect_uri=redirect_uri, allow=allow)
                location = response.headers['Location']
                self.assertEqual(location.count('?'), 1)
                self.assertIn('tenant=acme', location)
                self.assertIn(expected_param, location)

    def test_unregistered_redirect_uri_is_rejected(self):
        client_id = self._register_client(redirect_uris=[REDIRECT_URI])['client_id']
        response = self._authorize(client_id=client_id, redirect_uri='https://evil.example.com/callback')
        self.assertEqual(response.status_code, 400)

        response_json = response.json()
        self.assertEqual(response_json['error'], 'authorization_failed')
        self.assertEqual(response_json['error_description'], "redirect_uri is not registered for this client")
