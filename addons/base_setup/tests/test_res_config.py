# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestResConfig(TransactionCase):

    def test_multi_company_res_config_group(self):
        # Enable/Disable a group in a multi-company environment
        # 1/ All the users should be added/removed from the group
        # and not only the users of the allowed companies
        # 2/ The changes should be reflected for new users (Default User Template)

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

        ResConfig = self.env['res.config.settings']
        default_values = ResConfig.default_get(list(ResConfig.fields_get()))

        # Case 1: Enable a group
        default_values.update({'group_multi_currency': True})
        ResConfig.create(default_values).execute()
        self.assertTrue(user in self.env.ref('base.group_multi_currency').sudo().users)

        new_partner = self.env['res.partner'].create({'name': 'New User'})
        new_user = self.env['res.users'].create({
            'login': 'My First New User',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'partner_id': new_partner.id,
        })
        self.assertTrue(new_user in self.env.ref('base.group_multi_currency').sudo().users)

        # Case 2: Disable a group
        default_values.update({'group_multi_currency': False})
        ResConfig.create(default_values).execute()
        self.assertTrue(user not in self.env.ref('base.group_multi_currency').sudo().users)

        new_partner = self.env['res.partner'].create({'name': 'New User'})
        new_user = self.env['res.users'].create({
            'login': 'My Second New User',
            'company_id': company.id,
            'company_ids': [(4, company.id)],
            'partner_id': new_partner.id,
        })
        self.assertTrue(new_user not in self.env.ref('base.group_multi_currency').sudo().users)
