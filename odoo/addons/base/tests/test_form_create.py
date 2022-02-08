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
        partner_form = Form(self.env['res.partner'])
        partner_form.name = 'a partner'
        # YTI: Clean that brol
        if hasattr(self.env['res.partner'], 'property_account_payable_id'):
            property_account_payable_id = self.env['account.account'].create({
                'name': 'Test Account',
                'user_type_id': self.env.ref('account.data_account_type_payable').id,
                'code': 'TestAccountPayable',
                'reconcile': True
            })
            property_account_receivable_id = self.env['account.account'].create({
                'name': 'Test Account',
                'user_type_id': self.env.ref('account.data_account_type_receivable').id,
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
        country_form.save()

    def test_create_res_lang(self):
        lang_form = Form(self.env['res.lang'])
        lang_form.name = 'a lang name'
        lang_form.code = 'a lang code'
        lang_form.save()
