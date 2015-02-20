# -*- coding: utf-8 -*-

from openerp.tests import common


class TestAuthOAuthCommon(common.TransactionCase):
    
    def setUp(self):
        super(TestAuthOAuthCommon, self).setUp()
        BaseSetting = self.env['base.config.settings']
        
        self.oauth_setting = BaseSetting.create({
            'auth_oauth_google_enabled': True,
            'auth_oauth_google_client_id': 123456789
        })
