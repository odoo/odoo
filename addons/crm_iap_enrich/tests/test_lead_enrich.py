# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.iap.tests.common import MockIAPEnrich
from odoo.tests.common import users


class TestLeadEnrich(TestCrmCommon, MockIAPEnrich):

    @classmethod
    def setUpClass(cls):
        super(TestLeadEnrich, cls).setUpClass()
        cls.registry.enter_test_mode(cls.cr)

        cls.leads = cls.env['crm.lead']
        for x in range(0, 4):
            cls.leads += cls.env['crm.lead'].create({
                'name': 'Test %s' % x,
                'email_from': 'test_mail_%s@megaexample.com' % x
            })

    @classmethod
    def tearDownClass(cls):
        cls.registry.leave_test_mode()
        super().tearDownClass()

    @users('user_sales_manager')
    def test_enrich_internals(self):
        leads = self.env['crm.lead'].browse(self.leads.ids)
        leads[0].write({'partner_name': 'Already set', 'email_from': 'test@test1'})
        leads.flush_recordset()
        with self.mockIAPEnrichGateway(email_data={'test1': {'country_code': 'AU', 'state_code': 'NSW'}}):
            leads.iap_enrich()

        leads.flush_recordset()
        self.assertEqual(leads[0].partner_name, 'Already set')
        self.assertEqual(leads[0].country_id, self.env.ref('base.au'))
        self.assertEqual(leads[0].state_id, self.env.ref('base.state_au_2'))
        for lead in leads[1:]:
            self.assertEqual(lead.partner_name, 'Simulator INC')
        for lead in leads:
            self.assertEqual(lead.street, 'Simulator Street')

    # @users('sales_manager')
    # def test_enrich_error_credit(self):
    #     leads = self.env['crm.lead'].browse(self.leads.ids)
    #     with self.mockIAPEnrichGateway(sim_error='credit'):
    #         leads.iap_enrich()

    @users('user_sales_manager')
    def test_enrich_error_jsonrpc_exception(self):
        leads = self.env['crm.lead'].browse(self.leads.ids)
        with self.mockIAPEnrichGateway(sim_error='jsonrpc_exception'):
            leads.iap_enrich()

        for lead in leads:
            self.assertEqual(lead.street, False)
