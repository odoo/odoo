# -*- coding: utf-8 -*-

from openerp.addons.crm.tests.test_crm_access_group_users import TestCrmAccessGroupUsers

class TestCrmLeadOnchange(TestCrmAccessGroupUsers):

    def test_crm_lead_onchange(self):
        """ Tests for Test Crm Lead Onchange """
        CrmLead = self.env['crm.lead']
        CrmPhonecall = self.env['crm.phonecall']

        # Sales manager create a lead record to call a partner onchange, stage onchange and mailing opt-in onchange method.
        crm_case_25 = CrmLead.sudo(self.crm_res_users_salesmanager.id).create(
            dict(
                name='Need more info about your pc2',
                partner_id=self.env.ref('base.res_partner_2').id,
                lead_type='opportunity',
                stage_id=self.env.ref('crm.stage_lead1').id,
            ))

        # Sales manager create a lead record to call a mailing opt-out onchange method.
        crm_case_18 = CrmLead.sudo(self.crm_res_users_salesmanager.id).create(
            dict(
                name='Need 20 Days of Consultancy',
                lead_type='opportunity',
                stage_id=self.env.ref('crm.stage_lead1').id,
                opt_out=True,
            ))

        # Sales manager create a phonecall record to call a partner onchange method.
        crm_phonecall_5 = CrmPhonecall.sudo(self.crm_res_users_salesmanager.id).create(
            dict(
                name='Bad time',
                partner_id=self.env.ref('base.res_partner_5').id,
            ))
