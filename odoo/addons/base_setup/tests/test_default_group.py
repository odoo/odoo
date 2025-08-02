# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestResConfig(TransactionCase):

    def setUp(self):
        super(TestResConfig, self).setUp()

        self.user = self.env.ref('base.user_admin')
        self.company = self.env['res.company'].create({'name': 'oobO'})
        self.user.write({'company_ids': [(4, self.company.id)], 'company_id': self.company.id})
        Settings = self.env['res.config.settings'].with_user(self.user.id)
        self.config = Settings.create({})

    def test_multi_company_res_config_group(self):
        # Add a group to the template user
        # 1/ default_user_rights_minimal=False All the existing and new users should be
        # added to the group
        # 2/ default_user_rights_minimal=True The changes should not be reflected

        company = self.env['res.company'].create({'name': 'My Last Company'})
        partner = self.env['res.partner'].create({
            'name': 'My User'
        })
        user = self.env['res.users'].create({
            'login': 'My User',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'partner_id': partner.id,
        })
        group_multi_currency = self.env.ref('base.group_multi_currency')

        # Sanity check
        self.assertTrue(user not in group_multi_currency.users)

        # Propage new groups (default)
        self.env['ir.config_parameter'].sudo().set_param("base_setup.default_user_rights_minimal", False)

        # i.e. a group is added to the template user the installation of a module
        self.env.ref('base.default_user').groups_id |= group_multi_currency

        self.assertTrue(user in self.env.ref('base.group_multi_currency').sudo().users)

        new_partner = self.env['res.partner'].create({'name': 'New User'})
        new_user = self.env['res.users'].create({
            'login': 'My First New User',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'partner_id': new_partner.id,
        })
        self.assertTrue(new_user in group_multi_currency.users)

        (user | self.env.ref('base.default_user')).groups_id -= group_multi_currency

        # Again but invert the settings
        self.env['ir.config_parameter'].sudo().set_param("base_setup.default_user_rights_minimal", True)

        self.env.ref('base.default_user').groups_id |= group_multi_currency

        self.assertTrue(user not in group_multi_currency.users)

        new_partner = self.env['res.partner'].create({'name': 'New User'})
        new_user = self.env['res.users'].create({
            'login': 'My Second New User',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'partner_id': new_partner.id,
        })
        self.assertTrue(new_user not in group_multi_currency.users)
