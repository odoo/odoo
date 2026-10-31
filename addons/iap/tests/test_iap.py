# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, new_test_user


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

    def test_internal_user_creates_account(self):
        """ Internal users may create IAP accounts (e.g. the first lookup of
        partner_autocomplete) but not write on them: create() must not need
        a write to set the default name. """
        service = self.env['iap.service'].create({
            'name': 'Random Service',
            'description': 'test service',
            'unit_name': 'credit',
            'integer_balance': True,
            'technical_name': 'random_service_name',
        })
        user = new_test_user(self.env, login='internal_user', groups='base.group_user')
        account = self.env['iap.account'].with_user(user).create({'service_id': service.id})
        self.assertEqual(account.name, 'Random Service')

        self.env['ir.config_parameter'].set_param('database.is_neutralized', True)
        account = self.env['iap.account'].with_user(user).create({'service_id': service.id})
        self.assertTrue(account.sudo().account_token.endswith('+disabled'))
