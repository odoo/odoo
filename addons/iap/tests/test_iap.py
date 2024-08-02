# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestIAP(TransactionCase):
    def test_get_account(self):
        service_name = 'random_service_name'
        self.env['iap.service'].create({
            'name': service_name,
            'description': 'test service',
            'unit_name': 'credit',
            'integer_balance': True,
            'technical_name': service_name,
        })
        account = self.env['iap.account'].get(service_name)
        self.assertTrue(account.account_token, "Must be able to read the field")
