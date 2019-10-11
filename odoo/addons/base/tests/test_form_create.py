# -*- coding: utf-8 -*-
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
