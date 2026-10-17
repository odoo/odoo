# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


class TestIAP(TransactionCaseWithUserDemo):
    def test_get_iap_account(self):
        user_demo = self.user_demo
        user_admin = self.ref("base.user_admin")
        service_name = 'random_service_name'

        self.env['iap.service'].create({
            'name': service_name,
            'description': 'test service',
            'unit_name': 'credit',
            'integer_balance': True,
            'technical_name': service_name,
        })

        account = self.env['iap.account'].with_user(user_demo).get('random_service_name')

        # User demo can access an IAP account but not its token (must sudo)
        with self.assertRaises(AccessError):
            self.assertTrue(account.with_user(user_demo).account_token)

        # Admin can access the token
        self.assertTrue(account.with_user(user_admin).account_token, "Must be able to read the field")
