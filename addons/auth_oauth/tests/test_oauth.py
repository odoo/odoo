# -*- coding: utf-8 -*-

from openerp.addons.auth_oauth.tests.common import TestAuthOAuthCommon

class TestAuthOAuth(TestAuthOAuthCommon):

    def test_00_set_oauth_provider(self):
        """
            Testting set oauth provider.
        """
        auth_provider = self.oauth_setting.set_oauth_providers()
        self.assertEqual(auth_provider,None,
            'auth_oauth: Provider not set')
