# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged, Form


@tagged('-at_install', 'post_install')
class TestFormCreate(TransactionCase):
    """
    Test that the basic Odoo models records can be created on
    the interface.
    """

    def test_create_res_partner(self):
        # YTI: Clean that brol
        if hasattr(self.env['res.partner'], 'property_account_payable_id'):
            # Required for `property_account_payable_id`, `property_account_receivable_id` to be visible in the view
            # By default, it's the `group` `group_account_readonly` which is required to see it, in the `account` module
            # But once `account_accountant` gets installed, it becomes `account.group_account_user`
            # https://github.com/odoo/enterprise/commit/68f6c1f9fd3ff6762c98e1a405ade035129efce0
            self.env.user.groups_id += self.env.ref('account.group_account_readonly')
            self.env.user.groups_id += self.env.ref('account.group_account_user')
        partner_form = Form(self.env['res.partner'])
        partner_form.name = 'a partner'
        # YTI: Clean that brol
        if hasattr(self.env['res.partner'], 'property_account_payable_id'):
            property_account_payable_id = self.env['account.account'].create({
                'name': 'Test Account',
                'account_type': 'liability_payable',
                'code': 'TestAccountPayable',
                'reconcile': True
            })
            property_account_receivable_id = self.env['account.account'].create({
                'name': 'Test Account',
                'account_type': 'asset_receivable',
                'code': 'TestAccountReceivable',
                'reconcile': True
            })
            partner_form.property_account_payable_id = property_account_payable_id
            partner_form.property_account_receivable_id = property_account_receivable_id
        partner_form.save()

    def test_create_res_users(self):
        user_form = Form(self.env['res.users'])
        user_form.login = 'a user login'
        user_form.name = 'a user name'
        user_form.save()

    def test_create_res_company(self):
        company_form = Form(self.env['res.company'])
        company_form.name = 'a company'
        company_form.save()

    def test_create_res_group(self):
        group_form = Form(self.env['res.groups'])
        group_form.name = 'a group'
        group_form.save()

    def test_create_res_bank(self):
        bank_form = Form(self.env['res.bank'])
        bank_form.name = 'a bank'
        bank_form.save()

    def test_create_res_country(self):
        country_form = Form(self.env['res.country'])
        country_form.name = 'a country'
        country_form.code = 'ZX'
        country_form.save()

    def test_create_res_lang(self):
        lang_form = Form(self.env['res.lang'])
        # lang_form.url_code = 'LANG'  # invisible field, tested in http_routing
        lang_form.name = 'a lang name'
        lang_form.code = 'a lang code'
        lang_form.save()
