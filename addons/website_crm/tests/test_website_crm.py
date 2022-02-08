# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteCrm(odoo.tests.HttpCase):

    def test_tour(self):
        # change action to create opportunity
        self.start_tour("/", 'website_crm_pre_tour', login='admin')
        self.start_tour("/", 'website_crm_tour')

        # check result
        record = self.env['crm.lead'].search([('description', '=', '### TOUR DATA ###')])
        self.assertEqual(len(record), 1)
        self.assertEqual(record.contact_name, 'John Smith')
        self.assertEqual(record.email_from, 'john@smith.com')
        self.assertEqual(record.partner_name, 'Odoo S.A.')

    def test_catch_logged_partner_info_tour(self):
        user_login = 'admin'
        user_partner = self.env['res.users'].search([('login', '=', user_login)]).partner_id
        partner_email = user_partner.email
        partner_phone = user_partner.phone

        # no edit on prefilled data from logged partner : propagate partner_id on created lead
        self.start_tour("/", 'website_crm_pre_tour', login=user_login)
        self.start_tour("/", "website_crm_catch_logged_partner_info_tour", login=user_login)
        created_lead = self.env['crm.lead'].search([('description', '=', '### TOUR DATA PREFILL ###')])
        self.assertEqual(created_lead.partner_id, user_partner)

        # edited contact us partner info : do not propagate partner_id on lead
        self.start_tour("/", "website_crm_tour", login=user_login)
        created_lead = self.env['crm.lead'].search([('description', '=', '### TOUR DATA ###')])
        self.assertFalse(created_lead.partner_id)
        # check partner has not been changed
        self.assertEqual(user_partner.email, partner_email)
        self.assertEqual(user_partner.phone, partner_phone)
