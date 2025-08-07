# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteCrm(odoo.tests.HttpCase):

    def test_tour(self):
        all_utm_campaign = self.env['utm.campaign'].search([])
        utm_medium = self.env['utm.medium'].create({'name': 'Medium'})
        utm_source = self.env['utm.source'].create({'name': 'Source'})
        # change action to create opportunity
        self.start_tour(self.env['website'].get_client_action_url('/contactus'), 'website_crm_pre_tour', login='admin')
        self.start_tour("/?utm_source=Source&utm_medium=Medium&utm_campaign=New campaign", 'website_crm_tour')

        # check result
        record = self.env['crm.lead'].search([('description', '=', '<p>### TOUR DATA ###</p>')])
        self.assertEqual(len(record), 1)
        self.assertEqual(record.contact_name, 'John Smith')
        self.assertEqual(record.email_from, 'john@smith.com')
        self.assertEqual(record.partner_name, 'Odoo S.A.')

        # check UTM records
        self.assertEqual(record.source_id, utm_source)
        self.assertEqual(record.medium_id, utm_medium)
        self.assertNotIn(record.campaign_id, all_utm_campaign, 'Should have created a new campaign')
        self.assertEqual(record.campaign_id.name, 'New campaign', 'Name of the "on the fly" created campaign is wrong')

    def test_catch_logged_partner_info_tour(self):
        self.env.ref('base.partner_admin').write({
            'name': 'Mitchell Admin',
            'company_name': 'YourCompany',
            'email': 'mitchell.admin@example.com',
        })
        user_login = 'admin'
        user_partner = self.env['res.users'].search([('login', '=', user_login)]).partner_id
        partner_email = user_partner.email
        partner_phone = user_partner.phone

        # no edit on prefilled data from logged partner : propagate partner_id on created lead
        self.start_tour(self.env['website'].get_client_action_url('/contactus'), 'website_crm_pre_tour', login=user_login)

        with odoo.tests.RecordCapturer(self.env['crm.lead']) as capt:
            self.start_tour("/", "website_crm_catch_logged_partner_info_tour", login=user_login)
        self.assertEqual(capt.records.partner_id, user_partner)

        # edited contact us partner info : do not propagate partner_id on lead
        with odoo.tests.RecordCapturer(self.env['crm.lead']) as capt:
            self.start_tour("/", "website_crm_tour", login=user_login)
        self.assertFalse(capt.records.partner_id)

        # check partner has not been changed
        self.assertEqual(user_partner.email, partner_email)
        self.assertEqual(user_partner.phone, partner_phone)
