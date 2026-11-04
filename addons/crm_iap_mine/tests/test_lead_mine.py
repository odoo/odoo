# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.crm_iap_mine.tests.common import MockIAPReveal
from odoo.tests.common import users


class TestLeadMine(TestCrmCommon, MockIAPReveal):

    @classmethod
    def setUpClass(cls):
        super(TestLeadMine, cls).setUpClass()
        cls.registry.enter_test_mode(cls.cr)

        cls.test_crm_tags = cls.env['crm.tag'].create([
            {'name': 'TestTag1'},
            {'name': 'TestTag2'}
        ])
        cls.test_request = cls.env['crm.iap.lead.mining.request'].create({
            'contact_number': 3,
            'error_type': False,
            'lead_number': 3,
            'lead_type': 'lead',
            'name': 'Test Mine',
            'search_type': 'people',
            'state': 'draft',
            'tag_ids': [(6, 0, cls.test_crm_tags.ids)],
            'team_id':  cls.sales_team_1.id,
            'user_id': cls.user_sales_leads.id,
        })

    @classmethod
    def tearDownClass(cls):
        cls.registry.leave_test_mode()
        super().tearDownClass()

    @users('user_sales_manager')
    def test_mine_error_credit(self):
        mine_request = self.env['crm.iap.lead.mining.request'].browse(self.test_request.ids)
        with self.mock_IAP_mine(mine_request, sim_error='credit'):
            mine_request.action_submit()

        self.assertEqual(mine_request.error_type, 'credits')
        self.assertEqual(mine_request.state, 'error')

    @users('user_sales_manager')
    def test_mine_error_jsonrpc_exception(self):
        mine_request = self.env['crm.iap.lead.mining.request'].browse(self.test_request.ids)
        with self.assertRaises(exceptions.UserError):
            with self.mock_IAP_mine(mine_request, sim_error='jsonrpc_exception'):
                mine_request.action_submit()

    @users('user_sales_manager')
    def test_mine_error_no_result(self):
        mine_request = self.env['crm.iap.lead.mining.request'].browse(self.test_request.ids)
        with self.mock_IAP_mine(mine_request, sim_error='no_result'):
            mine_request.action_submit()

        self.assertEqual(mine_request.error_type, 'no_result')
        self.assertEqual(mine_request.state, 'draft')

    @users('user_sales_manager')
    def test_mine_wpeople(self):
        country_de = self.base_de
        state_de = self.de_state_st

        mine_request = self.env['crm.iap.lead.mining.request'].browse(self.test_request.ids)
        with self.mock_IAP_mine(mine_request, name_list=['Heinrich', 'Rivil', 'LidGen']):
            mine_request.action_submit()

        self.assertFalse(mine_request.error_type)
        self.assertEqual(mine_request.state, 'done')

        self.assertEqual(len(self._new_leads), 3, 'Number of leads should match mine request')

        for base_name in ['Heinrich', 'Rivil', 'LidGen']:
            lead = self._new_leads.filtered(lambda lead: lead.name == '%s GmbH' % base_name)
            self.assertTrue(bool(lead))

            # mine information
            self.assertEqual(lead.type, 'lead')
            self.assertEqual(lead.tag_ids, self.test_crm_tags)
            self.assertEqual(lead.team_id, self.sales_team_1)
            self.assertEqual(lead.user_id, self.user_sales_leads)
            # iap
            self.assertEqual(lead.reveal_id, '123456789', 'Ensure reveal_id is set to Duns')
            # DnB information
            self.assertFalse(lead.contact_name)
            self.assertEqual(lead.city, 'Mönchengladbach')
            self.assertEqual(lead.country_id, country_de)
            self.assertFalse(lead.partner_id)
            self.assertEqual(lead.partner_name, '%s GmbH' % base_name)
            self.assertEqual(lead.phone, '4930499193937')
            self.assertEqual(lead.state_id, state_de)
            self.assertEqual(lead.street, 'Mennrather Str. 123456')
            self.assertEqual(lead.website, 'https://%s.de' % base_name)
            self.assertEqual(lead.zip, '41179')

    @users('user_sales_manager')
    def test_mine_wcompany(self):
        country_de = self.base_de
        state_de = self.de_state_st

        mine_request = self.env['crm.iap.lead.mining.request'].browse(self.test_request.ids)
        mine_request.write({'search_type': 'companies'})
        with self.mock_IAP_mine(mine_request, name_list=['Heinrich', 'Rivil', 'LidGen']):
            mine_request.action_submit()

        self.assertFalse(mine_request.error_type)
        self.assertEqual(mine_request.state, 'done')

        self.assertEqual(len(self._new_leads), 3, 'Number of leads should match mine request')

        for base_name in ['Heinrich', 'Rivil', 'LidGen']:
            lead = self._new_leads.filtered(lambda lead: lead.name == '%s GmbH' % base_name)
            self.assertTrue(bool(lead))

            # mine information
            self.assertEqual(lead.type, 'lead')
            self.assertEqual(lead.tag_ids, self.test_crm_tags)
            self.assertEqual(lead.team_id, self.sales_team_1)
            self.assertEqual(lead.user_id, self.user_sales_leads)
            # iap
            self.assertEqual(lead.reveal_id, '123456789', 'Ensure reveal_id is set to Duns')
            # DnB information
            self.assertFalse(lead.contact_name)
            self.assertEqual(lead.city, 'Mönchengladbach')
            self.assertEqual(lead.country_id, country_de)
            self.assertFalse(lead.partner_id)
            self.assertEqual(lead.partner_name, '%s GmbH' % base_name)
            self.assertEqual(lead.phone, '4930499193937')
            self.assertEqual(lead.state_id, state_de)
            self.assertEqual(lead.street, 'Mennrather Str. 123456')
            self.assertEqual(lead.website, 'https://%s.de' % base_name)
            self.assertEqual(lead.zip, '41179')
