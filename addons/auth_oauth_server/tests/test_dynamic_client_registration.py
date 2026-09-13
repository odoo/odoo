from odoo.tests import tagged

from .common import OauthServerCommon


@tagged('post_install', '-at_install')
class TestDynamicClientRegistration(OauthServerCommon):

    def test_client_registration(self):
        response = self._register_client(auth_method='client_secret_post')
        self.assertTrue(response['client_id'])
        self.assertTrue(response['client_secret'])

        # A client secret is generated if token_endpoint_auth_method is missing.
        # token_endpoint_auth_method will default to client_secret_basic in this case.
        response = self._register_client(auth_method=None)
        self.assertTrue(response['client_secret'])

        # No client secret is generated if auth_method = "none" (public clients).
        response = self._register_client(auth_method="none")
        self.assertNotIn('client_secret', response)

        response = self._register_client(auth_method="abcd")
        self.assertEqual(response['error'], 'invalid_client_metadata')
        self.assertEqual(response['error_description'], 'Unsupported token_endpoint_auth_method abcd')

    def test_register_with_unknown_resource(self):
        response = self._register_client(resource="notfound")
        self.assertEqual(response['error'], "invalid_resource")
        self.assertEqual(response['error_description'], "OAuth resource notfound isn't available")

    def test_register_allows_https_or_loopback_only_http_redirect_uri(self):
        response = self._register_client(redirect_uris=["https://www.example.com:8080/cb"])
        self.assertNotIn('error', response)
        self.assertIn('client_id', response)
        self.assertIn('client_secret', response)

        response = self._register_client(redirect_uris=["http://127.0.0.1:8080/cb"])
        self.assertNotIn('error', response)
        self.assertIn('client_id', response)
        self.assertIn('client_secret', response)

        response = self._register_client(redirect_uris=[])
        self.assertEqual(response['error'], "invalid_client_metadata")

        response = self._register_client(redirect_uris=["http://client.example.com/callback"])
        self.assertEqual(response['error'], 'invalid_client_metadata')

        response = self._register_client(["http://localhost:8080/cb"])
        self.assertEqual(response['error'], 'invalid_client_metadata')

        response = self._register_client(["https://www.example.com:1234/cb", "http://localhost:8080/cb"])
        self.assertEqual(response['error'], 'invalid_client_metadata')

    def test_register_rejects_redirect_uri_with_fragment(self):
        response = self._register_client(redirect_uris=["https://client.example.com/cb#fragment"])
        self.assertEqual(response['error'], 'invalid_client_metadata')
